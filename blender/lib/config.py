"""Config loading, validation, CLI parsing and deterministic seeding.

Everything content-related comes from content/golu.config.json (SPEC §3, DECISIONS D19).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

RGB = tuple[float, float, float]

ROOT = Path(__file__).resolve().parents[2]
BLENDER_DIR = ROOT / "blender"

VALID_ARMS = {0, 2, 4, 6, 8, 10}          # 6 added per DECISIONS D02
VALID_ROWS = {"front", "back"}
VALID_MARKS = {"namam", "vibhuti", "tilak_dot", "tilak_vertical", "none"}
MARK_IDS = {"none": 0, "tilak_dot": 1, "namam": 2, "vibhuti": 3, "tilak_vertical": 4}

_SEED_BASE = 0


# --------------------------------------------------------------------------- dataclasses
@dataclass(frozen=True)
class AttireSpec:
    lower: str
    upper: str
    color: str
    accent: str
    zari: str


@dataclass(frozen=True)
class PositionSpec:
    slot: int
    x: float
    row: Literal["front", "back"]
    turn: float


@dataclass(frozen=True)
class DollSpec:
    id: str
    step: int
    name_en: str
    name_ta: str
    archetype: str
    model: str | None
    skin: str
    arms: int
    attire: AttireSpec | None
    attributes: tuple[str, ...]
    extras: tuple[str, ...]
    vahana: str | None
    seat: str
    pose: str
    forehead: str | None
    scale: float
    position: PositionSpec


@dataclass(frozen=True)
class StepSpec:
    id: int
    title_en: str
    cloth_color: str
    story_props: tuple[str, ...]
    dolls: tuple[DollSpec, ...]


class Palette:
    """Wraps config.palette; every lookup returns linear RGB."""

    def __init__(self, raw: dict):
        self.raw = raw

    def _get(self, group: str, key: str) -> RGB:
        try:
            return srgb_hex_to_linear(self.raw[group][key])
        except KeyError as exc:
            raise KeyError(f"palette.{group}.{key} missing from config") from exc

    def silk(self, key: str) -> RGB:
        return self._get("silk", key)

    def skin(self, key: str) -> RGB:
        return self._get("skin", key)

    def cloth(self, key: str) -> RGB:
        return self._get("cloth", key)

    def material(self, key: str) -> RGB:
        return self._get("materials", key)

    def token(self, key: str) -> RGB:
        return self._get("tokens", key)

    def kelvin(self, key: str) -> float:
        return float(self.raw["light_kelvin"][key])


@dataclass(frozen=True)
class GoluConfig:
    raw: dict
    layout: dict
    palette: Palette
    steps: tuple[StepSpec, ...]
    prasadam: dict
    seed: int
    path: Path

    def doll(self, doll_id: str) -> DollSpec:
        for s in self.steps:
            for d in s.dolls:
                if d.id == doll_id:
                    return d
        raise KeyError(doll_id)

    def all_dolls(self) -> list[DollSpec]:
        return [d for s in self.steps for d in s.dolls]

    def step(self, n: int) -> StepSpec:
        return self.steps[n - 1]


@dataclass(frozen=True)
class CliArgs:
    config: Path
    quality: Literal["draft", "final"]
    steps: list[int]
    out: Path
    empty: bool
    verify: bool
    only: list[str]
    stride: int
    resume: bool
    frames: list[int] | None
    qa_stills: bool
    probe: bool
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- helpers
def srgb_hex_to_linear(hexstr: str) -> RGB:
    h = hexstr.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"bad colour {hexstr!r}")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2])


def parse_steps(spec: str) -> list[int]:
    result: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            result.extend(range(int(a), int(b) + 1))
        else:
            result.append(int(part))
    bad = [n for n in result if not 1 <= n <= 9]
    if bad:
        raise ValueError(f"steps out of range 1-9: {bad}")
    return sorted(set(result))


def parse_frames(spec: str | None) -> list[int] | None:
    if not spec:
        return None
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return out


def parse_cli(argv: list[str], extra_flags: dict[str, dict] | None = None) -> CliArgs:
    """Parse the arguments that follow Blender's `--` separator."""
    args_after = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser(prog="golu", add_help=True)
    p.add_argument("--config", default=str(ROOT / "content" / "golu.config.json"))
    p.add_argument("--quality", choices=["draft", "final"], default="draft")
    p.add_argument("--steps", default="1-9")
    p.add_argument("--out", default=str(ROOT / "renders"))
    p.add_argument("--empty", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--only", default="")
    p.add_argument("--stride", type=int, default=1)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--frames", default=None)
    p.add_argument("--qa-stills", action="store_true")
    p.add_argument("--probe", action="store_true")
    for name, kw in (extra_flags or {}).items():
        p.add_argument(name, **kw)
    ns = p.parse_args(args_after)
    extra = {k.lstrip("-").replace("-", "_"): getattr(ns, k.lstrip("-").replace("-", "_"))
             for k in (extra_flags or {})}
    return CliArgs(
        config=Path(ns.config).resolve(),
        quality=ns.quality,
        steps=parse_steps(ns.steps),
        out=Path(ns.out).resolve(),
        empty=ns.empty,
        verify=ns.verify,
        only=[s for s in ns.only.split(",") if s],
        stride=max(1, ns.stride),
        resume=not ns.no_resume,
        frames=parse_frames(ns.frames),
        qa_stills=ns.qa_stills,
        probe=ns.probe,
        extra=extra,
    )


# --------------------------------------------------------------------------- validation
def validate_config(raw: dict) -> list[str]:
    errs: list[str] = []
    for key in ("meta", "layout", "palette", "ui", "steps", "rituals", "prasadam", "audio"):
        if key not in raw:
            errs.append(f"missing top-level key '{key}'")
    if errs:
        return errs
    pal = raw["palette"]
    for grp in ("tokens", "skin", "silk", "cloth", "materials", "light_kelvin"):
        if grp not in pal:
            errs.append(f"palette.{grp} missing")
    steps = raw["steps"]
    if [s.get("id") for s in steps] != list(range(1, 10)):
        errs.append("steps must have ids 1..9 in order")
    ids: set[str] = set()
    for s in steps:
        sid = s.get("id")
        for k in ("title_en", "title_ta", "story_en", "story_ta", "alt_en", "alt_ta", "cloth_color", "dolls"):
            if k not in s:
                errs.append(f"step {sid}: missing {k}")
        if s.get("cloth_color") not in pal.get("cloth", {}):
            errs.append(f"step {sid}: cloth_color {s.get('cloth_color')!r} not in palette.cloth")
        prev_slot, prev_x = 0, -2.0
        for d in s.get("dolls", []):
            did = d.get("id", "?")
            if did in ids:
                errs.append(f"duplicate doll id {did}")
            ids.add(did)
            for k in ("name_en", "name_ta", "archetype", "skin", "arms", "attire", "attributes",
                      "vahana", "pose", "scale", "position", "info_en", "info_ta", "seat"):
                if k not in d:
                    errs.append(f"{did}: missing {k}")
            if d.get("arms") not in VALID_ARMS:
                errs.append(f"{did}: arms {d.get('arms')} not in {sorted(VALID_ARMS)}")
            if d.get("skin") not in pal.get("skin", {}):
                errs.append(f"{did}: skin {d.get('skin')!r} not in palette.skin")
            arch = d.get("archetype")
            if arch == "object" and not d.get("model"):
                errs.append(f"{did}: object without model")
            if arch not in ("object", "animal") and len(d.get("attributes", [])) != d.get("arms"):
                errs.append(f"{did}: {len(d.get('attributes', []))} attributes for {d.get('arms')} arms")
            if arch == "animal" and not d.get("vahana"):
                errs.append(f"{did}: animal without vahana species")
            att = d.get("attire")
            if att:
                for k in ("lower", "upper", "color", "accent", "zari"):
                    if k not in att:
                        errs.append(f"{did}: attire.{k} missing")
                for k in ("color", "accent"):
                    if att.get(k) not in pal.get("silk", {}):
                        errs.append(f"{did}: attire.{k} {att.get(k)!r} not in palette.silk")
            fh = d.get("forehead")
            if fh is not None and fh not in VALID_MARKS:
                errs.append(f"{did}: forehead {fh!r} invalid")
            pos = d.get("position", {})
            if pos.get("row") not in VALID_ROWS:
                errs.append(f"{did}: position.row invalid")
            x = float(pos.get("x", 0))
            if not -1.0 <= x <= 1.0:
                errs.append(f"{did}: position.x {x} outside -1..1")
            slot = int(pos.get("slot", 0))
            if slot != prev_slot + 1:
                errs.append(f"{did}: slot {slot} out of sequence (expected {prev_slot + 1})")
            if x < prev_x:
                errs.append(f"{did}: x {x} is left of the previous slot ({prev_x})")
            prev_slot, prev_x = slot, x
            if not 0.3 <= float(d.get("scale", 1)) <= 2.0:
                errs.append(f"{did}: scale out of range")
    pr = raw["prasadam"]
    dish_ids = {d["id"] for d in pr.get("dishes", [])}
    if pr.get("third_dish") not in pr.get("third_dish_options", []):
        errs.append("prasadam.third_dish not among third_dish_options")
    for k in list(pr.get("fixed", [])) + list(pr.get("third_dish_options", [])):
        if k not in dish_ids:
            errs.append(f"prasadam dish {k} not defined")
    return errs


def _doll_from_raw(d: dict, step: int) -> DollSpec:
    att = d.get("attire")
    pos = d["position"]
    return DollSpec(
        id=d["id"], step=step, name_en=d["name_en"], name_ta=d["name_ta"],
        archetype=d["archetype"], model=d.get("model"), skin=d["skin"], arms=int(d["arms"]),
        attire=AttireSpec(**att) if att else None,
        attributes=tuple(d.get("attributes", [])), extras=tuple(d.get("extras", [])),
        vahana=d.get("vahana"), seat=d.get("seat", "pedestal"), pose=d.get("pose", "standing"),
        forehead=d.get("forehead"), scale=float(d.get("scale", 1.0)),
        position=PositionSpec(slot=int(pos["slot"]), x=float(pos["x"]), row=pos["row"],
                              turn=float(pos.get("turn", 0.0))),
    )


def load_config(path: Path) -> GoluConfig:
    global _SEED_BASE
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    errs = validate_config(raw)
    if errs:
        raise ValueError("config invalid:\n  " + "\n  ".join(errs))
    steps = tuple(
        StepSpec(id=s["id"], title_en=s["title_en"], cloth_color=s["cloth_color"],
                 story_props=tuple(s.get("story_props", [])),
                 dolls=tuple(_doll_from_raw(d, s["id"]) for d in s["dolls"]))
        for s in raw["steps"])
    seed = int(raw["meta"].get("seed", 0))
    _SEED_BASE = seed
    return GoluConfig(raw=raw, layout=raw["layout"], palette=Palette(raw["palette"]), steps=steps,
                      prasadam=raw["prasadam"], seed=seed, path=Path(path).resolve())


# --------------------------------------------------------------------------- determinism
def seed_for(*keys: object) -> int:
    """Stable 31-bit seed from a key path (never Python's salted hash())."""
    h = zlib.crc32("/".join(str(k) for k in keys).encode("utf-8"))
    return (h ^ (_SEED_BASE * 2654435761)) & 0x7FFFFFFF


def rng_for(*keys: object) -> random.Random:
    return random.Random(seed_for(*keys))


def config_hash(path: Path) -> str:
    """SHA-1 over the config and every Blender script, used to detect stale .blend builds."""
    h = hashlib.sha1()
    h.update(Path(path).read_bytes())
    for f in sorted(BLENDER_DIR.rglob("*.py")):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]
