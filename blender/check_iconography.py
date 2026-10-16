"""Verify every config doll against the rules table in ICONOGRAPHY.md (SPEC §4.3).

blender -b --factory-startup -P blender/check_iconography.py -- --config content/golu.config.json
Exit code 1 on any violation.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import config as C  # noqa: E402

# archetype default forehead marks (PLAN §3.2); a doll's own `forehead` overrides
DEFAULT_MARKS = {
    "deity_vishnu_form": "namam", "avatar_matsya": "namam", "avatar_kurma": "namam", "avatar_varaha": "namam",
    "avatar_narasimha": "namam", "vamana_vatu": "namam", "sage_warrior": "namam", "prince": "namam",
    "king": "namam", "musician": "vibhuti", "goddess": "tilak_dot", "goddess_consort": "tilak_dot",
    "goddess_warrior": "tilak_dot", "deity_murugan": "vibhuti", "deity_ganesha": "vibhuti",
    "tribal_girl": "tilak_dot", "village_woman": "tilak_dot", "village_man": "vibhuti", "chettiar": "vibhuti",
    "modern_woman": "tilak_dot", "modern_man": "none", "schoolchild_girl": "tilak_dot", "schoolchild_boy": "none",
    "saint_vaishnava": "namam", "saint_andal": "namam", "saint_shaiva": "vibhuti", "child_saint": "vibhuti",
    "poet_sage": "none", "elder_woman": "vibhuti", "infant_krishna": "namam", "child_krishna": "namam",
    "marapachi": "none", "sage": "namam", "animal": "none", "object": "none",
}


@dataclass
class Rule:
    rid: str
    applies: list[str]
    skin: list[str]
    arms: list[str]
    must: list[str]
    vahana: list[str]
    forehead: list[str]
    attire: list[str]
    notes: str


def _alts(cell: str) -> list[str]:
    cell = cell.strip().replace("\\|", "|")
    if cell in ("", "-"):
        return []
    return [c.strip() for c in cell.split("|") if c.strip()]


def parse_rules(md_path: Path) -> list[Rule]:
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"## 1\. Rules table(.*?)\n## ", text, re.S)
    if not m:
        raise ValueError("rules table section not found in ICONOGRAPHY.md")
    rules = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("| R"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) < 9:
            continue
        rid, applies, skin, arms, must, vahana, forehead, attire, notes = cells[:9]
        rules.append(Rule(rid, _alts(applies), _alts(skin), _alts(arms),
                          [x.strip() for x in must.split("+") if x.strip() and x.strip() != "-"],
                          _alts(vahana), _alts(forehead), _alts(attire), notes))
    return rules


def matches(rule: Rule, doll: C.DollSpec) -> bool:
    for a in rule.applies:
        if a.startswith("step:"):
            continue
        if a == doll.id or a == doll.archetype:
            return True
    return False


def _ok(allowed: list[str], value) -> bool:
    return not allowed or "*" in allowed or str(value) in allowed


def check(cfg: C.GoluConfig, rules: list[Rule]) -> tuple[list[str], dict[str, int]]:
    errs: list[str] = []
    hits: dict[str, int] = {r.rid: 0 for r in rules}
    for d in cfg.all_dolls():
        mark = d.forehead or DEFAULT_MARKS.get(d.archetype, "none")
        held = set(d.attributes) | set(d.extras)
        for r in rules:
            if not matches(r, d):
                continue
            hits[r.rid] += 1
            if not _ok(r.skin, d.skin):
                errs.append(f"{r.rid} {d.id}: skin {d.skin} not in {r.skin}")
            if not _ok(r.arms, d.arms):
                errs.append(f"{r.rid} {d.id}: arms {d.arms} not in {r.arms}")
            missing = [t for t in r.must if t not in held]
            if missing:
                errs.append(f"{r.rid} {d.id}: missing {missing}")
            if r.vahana and r.vahana != ["*"] and d.vahana not in r.vahana:
                errs.append(f"{r.rid} {d.id}: vahana {d.vahana} not in {r.vahana}")
            if not _ok(r.forehead, mark):
                errs.append(f"{r.rid} {d.id}: forehead {mark} not in {r.forehead}")
            col = d.attire.color if d.attire else None
            if not _ok(r.attire, col):
                errs.append(f"{r.rid} {d.id}: attire colour {col} not in {r.attire}")
    for r in rules:
        for a in r.applies:
            if not a.startswith("step:"):
                continue
            n = int(a.split(":")[1])
            dolls = cfg.step(n).dolls
            hits[r.rid] += 1
            if r.vahana and r.vahana != ["*"]:
                if not any(d.vahana in r.vahana for d in dolls):
                    errs.append(f"{r.rid} step {n}: no doll with vahana in {r.vahana}")
            if r.rid == "R28" and any(d.seat != "lotus_seat" for d in dolls):
                errs.append(f"R28 step {n}: every doll must have seat lotus_seat")
    for rid, n in hits.items():
        if n == 0:
            errs.append(f"{rid}: rule matched no doll (stale rule or renamed id)")
    return errs, hits


def main(argv: list[str]) -> int:
    args = C.parse_cli(argv)
    cfg = C.load_config(args.config)
    rules = parse_rules(C.ROOT / "ICONOGRAPHY.md")
    errs, hits = check(cfg, rules)
    for r in rules:
        status = "FAIL" if any(e.startswith(r.rid + " ") for e in errs) else "PASS"
        print(f"{r.rid:4s} {status}  ({hits[r.rid]} matched)  {', '.join(r.applies)}")
    for e in errs:
        print("ICONOGRAPHY FAIL:", e)
    print(f"ICONOGRAPHY: {len(rules)} rules, {len(cfg.all_dolls())} dolls, "
          f"{'PASS' if not errs else str(len(errs)) + ' violations'}")
    return 1 if errs else 0


if __name__ == "__main__":
    try:
        code = main(sys.argv)
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.exit(code)
