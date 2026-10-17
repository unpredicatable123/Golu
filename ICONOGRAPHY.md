# Iconography reference

This file is the rule set every doll in `content/golu.config.json` is checked against. It has two parts:

1. **Rules table:** machine-readable. `blender/check_iconography.py` parses it and fails the build on any violation.
2. **Per-doll sheet:** the visual points a reviewer confirms on the QA turntables (Phase 2) and the draft fly-through (Phase 3).

Conventions used below:
- **Hands** are listed as `[R1, L1, R2, L2, …]`. R1/L1 is the front (primary) pair; later pairs fan upward and back. "Right" is the doll's own right, which is the viewer's left.
- **Forehead marks:** `namam` is the Vaishnava U-shaped white namam with a red centre line; `vibhuti` is three horizontal ash stripes with a kumkum dot; `tilak_dot` is a kumkum pottu; `tilak_vertical` is a red vertical tilak; `none` means no mark.
- **Pitambara** (yellow silk) is Vishnu's and Krishna's garment. **Nilambara** (blue silk) is Balarama's.

## 1. Rules table

`skin`, `arms`, `forehead` and `vahana` list the allowed values (`|` separates options, `*` means any). `must_hold` lists tokens that must appear in `attributes[]` or `extras[]` (`+` means all of them). `attire` constrains `attire.color`.

| rule | applies_to | skin | arms | must_hold | vahana | forehead | attire | notes |
|---|---|---|---|---|---|---|---|---|
| R01 | avatar_matsya | blue | 4 | chakra+shankha | - | namam | pitambara | Fish lower body from the waist. |
| R02 | avatar_kurma | blue | 4 | chakra+shankha | - | namam | pitambara | Tortoise lower body; human torso rises from the shell. |
| R03 | avatar_varaha | blue | 4 | chakra+shankha+bhudevi | - | namam | pitambara | Boar head with two upturned tusks; Bhudevi held on the left arm. |
| R04 | avatar_narasimha | blue | 4 | chakra+shankha | - | namam | pitambara | Lion head with a full mane. Hiranyakashipu across the lap, stylised, no gore. |
| R05 | vamana_vatu | blue | 2 | chatra+kamandalu+kudumi+sacred_thread | - | namam | ivory | Brahmachari boy. Holds no shankha or chakra: exception E1. |
| R06 | sage_warrior | blue | 4 | chakra+shankha+parashu | - | namam | saffron | Parasurama: axe, jata, sacred thread. |
| R07 | s2_rama | blue | 4 | chakra+shankha+bow+arrow | - | namam | pitambara | Dasavatara form (four arms). |
| R08 | s2_balarama | peach | 4 | chakra+shankha+hala+musala | - | namam | nilambara | Fair complexion and blue garments: exception E2. |
| R09 | s2_krishna | blue | 4 | chakra+shankha+flute | - | namam | pitambara | Peacock feather in the crown. |
| R10 | s2_kalki | blue | 4 | chakra+shankha+khadga | horse | namam | pitambara | White horse, sword raised. |
| R11 | s3_rama | blue | 2 | garland | - | namam | pitambara | Narrative (human) form: two arms, no shankha or chakra (E3). |
| R12 | s3_sita | peach | 2 | garland+jasmine | - | tilak_dot | * | Bride; stands on Rama's left (viewer's right). |
| R13 | deity_murugan | peach | 2\|4\|12 | vel | - | vibhuti | * | Peacock present on the same step (rule R27). |
| R14 | goddess_consort | peach | 2\|4 | jasmine | - | tilak_dot | * | Sita, Deivanai. |
| R15 | deity_ganesha | elephant-grey | 4 | danta+modaka+ankusha+pasha | mouse | vibhuti | * | Right tusk broken (stump); the broken piece in R1. Trunk curls to his left toward the modak in L1. Pot belly; serpent as sacred thread. |
| R16 | s9_saraswati | peach | 4 | veena+japa_mala+palm_leaf | swan | tilak_dot | white | White saree with gold zari; seated on a white lotus. |
| R17 | s9_lakshmi | peach | 4 | padma+varada_coins | - | tilak_dot | rani-pink\|lotus-pink\|kumkum | Seated on a pink lotus; gold coins flow from L1. |
| R18 | s9_durga | peach | 8\|10 | trishula+chakra+shankha+khadga | lion | tilak_vertical | kumkum\|maroon | Rides the lion. |
| R19 | s8_adi | peach | 4 | abhaya+varada+padma+flag | - | tilak_dot | * | Lotus seat. |
| R20 | s8_dhanya | peach | 8 | padma+gada+paddy_sheaf+sugarcane+banana_bunch | - | tilak_dot | parrot-green\|mango-green | Green garments. |
| R21 | s8_dhairya | peach | 8 | chakra+shankha+bow+arrow+trishula+palm_leaf | - | tilak_dot | kumkum\|maroon | Red garments. |
| R22 | s8_gaja | peach | 4 | padma | gaja_pair | tilak_dot | kumkum\|maroon | Two elephants raise water pots over her. |
| R23 | s8_santana | peach | 6 | infant+khadga+shield+kalasam | - | tilak_dot | * | Child on her lap holds a lotus. Six arms: exception E4. |
| R24 | s8_vijaya | peach | 8 | chakra+shankha+khadga+shield+padma+pasha | - | tilak_dot | kumkum\|maroon | Red garments. |
| R25 | s8_vidya | peach | 4 | palm_leaf+peacock_quill | - | tilak_dot | kumkum\|white | Book of the Vedas and a peacock-feather pen. |
| R26 | s8_dhana | peach | 6 | chakra+shankha+kalasam+bow_arrow+padma+abhaya_coins | - | tilak_dot | kumkum\|rani-pink\|maroon | Six arms: exception E4. |
| R27 | step:4 | * | * | - | peacock | * | * | Step 4 must contain a peacock (Murugan's vahana). |
| R28 | step:8 | * | * | - | * | * | * | Every Step 8 doll has `seat: lotus_seat` (all eight sit on lotuses). |
| R29 | saint_vaishnava\|saint_andal | wheat\|peach | 2 | - | - | namam | * | Azhwars wear the namam. |
| R30 | saint_shaiva\|child_saint | wheat\|peach | 2 | rudraksha | - | vibhuti | * | Nayanmars wear vibhuti and rudraksha. |
| R31 | s6_andal | peach | 2 | parrot+andal_kondai+jasmine | - | namam | * | Parrot in her left hand (L1); side-tied kondai. |
| R32 | s6_sambandar | peach | 2 | point_up+milk_cup | - | vibhuti | * | Child; right forefinger points up, cup in the left hand. |
| R33 | s6_appar | wheat | 2 | uzhavarappadai_on_shoulder+anjali | - | vibhuti | * | Small hoe against the shoulder, hands joined. |
| R34 | s6_thiruvalluvar | wheat | 2 | palm_leaf+stylus+beard | - | none | white | The Tamil Nadu government portrait: white robes and no religious mark (E5). |
| R35 | s6_avvaiyar | wheat | 2 | walking_stick | - | vibhuti | white | Elderly; white saree. |
| R36 | s6_nammazhwar | wheat | 2 | chin+hridaya | - | namam | * | Seated in padmasana; right hand in upadesa (chin) mudra, left hand on his heart. |
| R37 | child_krishna\|infant_krishna | blue | 2 | peacock_feather_crown | - | namam | pitambara | Kannan in the Step 7 leelas. |
| R38 | s7_kaliya_krishna | blue | 2 | serpent_tail | kaliya | namam | pitambara | Dances on the hoods with one leg raised; holds Kaliya's tail in L1. Serpent painted `dark`. |
| R39 | s7_govardhana_krishna | blue | 2 | lift_hill_finger | - | namam | pitambara | Hill raised on the little finger of the left hand. |
| R40 | marapachi | red-sanders | 2 | - | - | * | * | Carved red-sanders wood, dressed in real-looking silk; no clay varnish. |

Exceptions (each one also appears in DECISIONS.md):

- **E1 Vamana:** shown as the brahmachari boy, two-armed with chatra and kamandalu, as in temple and craft depictions. The "Vishnu forms carry shankha + chakra" rule doesn't apply to this form. His Vishnu identity is carried by blue skin and the namam.
- **E2 Balarama:** the texts describe him as fair-skinned and dressed in blue, the reverse of Krishna. He keeps shankha and chakra (Dasavatara form) but not blue skin.
- **E3 Narrative forms:** Rama (Step 3) and Kannan (Step 7) are shown in their human lilas with two arms, as golu narrative sets show them. The four-armed shankha-chakra rule applies to the Dasavatara set on Step 2.
- **E4 Six arms:** Santana and Dhana Lakshmi are six-armed in the standard Ashta Lakshmi iconography, so the factory accepts `arms: 6` in addition to 2, 4, 8 and 10.
- **E5 Thiruvalluvar:** no sectarian mark, following the Tamil Nadu government portrait in use since the 1960s.

## 2. Per-doll visual sheet

Status columns are filled in during the build: **C** = passes the config check, **T** = confirmed on the QA turntable (Phase 2; QA dolls only), **F** = confirmed in the draft fly-through (Phase 3).

| id | must read as | C | T | F |
|---|---|---|---|---|
| s1_pslv | White four-stage rocket with six strap-on boosters, inside a red-and-white lattice gantry | ✓ | – |  |
| s1_dish | White parabolic dish on a tilting mount | ✓ | – |  |
| s1_scientist_woman | Silk saree, jasmine, ID lanyard, joined hands of celebration | ✓ | – |  |
| s1_scientist_man | Shirt and trousers, spectacles, clipboard, pointing | ✓ | – |  |
| s1_chandrayaan | Gold-foil box lander on four legs, ramp, six-wheeled rover with a solar panel, on a grey cratered patch | ✓ | – |  |
| s1_child_girl | Pavadai-sattai, braids with jasmine, open laptop with a soft glowing screen | ✓ | – |  |
| s1_child_boy | School shirt and shorts, pointing at the laptop | ✓ | – |  |
| s1_vande_bharat | Aerodynamic nose; white body with a blue band (the original livery) on a short track | ✓ | – |  |
| s1_metro | Steel-grey coach with blue band, on a pillar-and-beam viaduct | ✓ | – |  |
| s2_matsya | Blue torso on a fish tail, scales, shankha (L2) and chakra (R2) | ✓ | – |  |
| s2_kurma | Blue torso rising from a domed shell with hex scutes | ✓ | – |  |
| s2_varaha | Boar head with upturned tusks, Bhudevi seated on the left arm | ✓ | – |  |
| s2_narasimha | Lion head, orange-gold mane, fangs, namam; stylised figure across the lap | ✓ | ✓ |  |
| s2_vamana | Small blue boy with palm-leaf umbrella, water pot, tuft, deerskin, sacred thread | ✓ | – |  |
| s2_parasurama | Axe in R1, matted hair, saffron veshti | ✓ | – |  |
| s2_rama | Bow and arrow in front hands, shankha-chakra behind, quiver | ✓ | ✓ |  |
| s2_balarama | Fair skin, blue garments, plough and pestle | ✓ | – |  |
| s2_krishna | Flute across both front hands, peacock feather, crossed legs | ✓ | – |  |
| s2_kalki | White horse with red caparison, sword raised | ✓ | – |  |
| s3_thavil | Barrel drum on a strap, stick and thimbles | ✓ | – |  |
| s3_nadaswaram | Long double-reed pipe with a flared bell | ✓ | – |  |
| s3_vasishta | White beard, jata, kamandalu | ✓ | – |  |
| s3_dasaratha | Crowned elderly king, moustache, maroon silk | ✓ | – |  |
| s3_lakshmana | Fair, green silk, bow on his shoulder, joined hands | ✓ | – |  |
| s3_rama | Blue, two arms, raising a thick garland, turned toward Sita | ✓ | – |  |
| s3_sita | Red bridal silk, jasmine, nose ring, garland raised, turned toward Rama | ✓ | ✓ |  |
| s3_janaka | Crowned king with beard, blessing | ✓ | – |  |
| s3_vishwamitra | Saffron robes, beard, staff | ✓ | – |  |
| s3_dhanush | Great curved bow in two pieces, gold-banded | ✓ | – |  |
| s4_valli | Green half-saree, sling raised, on a watch platform in the millet | ✓ | – |  |
| s4_elephant | Charging elephant, trunk raised, facing Valli | ✓ | – |  |
| s4_murugan | Vel with a leaf-shaped blade, kireedam, vibhuti, red silk | ✓ | ✓ |  |
| s4_peacock | Fanned tail of eye-feathers, iridescent blue neck | ✓ | ✓ |  |
| s4_deivanai | Yellow silk, blue water lily (nilotpala), on Murugan's left (viewer's right) | ✓ | – |  |
| s4_narada | Tambura, chipla, tuft, standing on a cloud | ✓ | – |  |
| s5_chettiar | Bare-chested with angavastram, moustache, gold chain, scales and ledger, seated at the counter | ✓ | ✓ |  |
| s5_chettichi | Brinjal-purple saree, measure in hand | ✓ | – |  |
| s5_vendor | Squatting with a basket of brinjal, drumsticks and greens | ✓ | – |  |
| s5_kolam_woman | Bent to the floor drawing a small kolam, bowl of rice flour | ✓ | – |  |
| s5_potter | Squatting at the wheel shaping a pot | ✓ | – |  |
| s5_cow | White cow, painted horns, kumkum on the forehead, neck bell | ✓ | – |  |
| s5_calf | Calf beside the cow | ✓ | – |  |
| s5_bullock_cart | Two humped grey-white bullocks with painted horns, wooden cart | ✓ | – |  |
| s5_cart_driver | Turban cloth, goad stick, on the yoke | ✓ | – |  |
| s6_periyazhwar | Joined hands, namam, tuft | ✓ | – |  |
| s6_andal | Side kondai with jasmine, parrot on her left hand, lotus in her right | ✓ | – |  |
| s6_nammazhwar | Seated padmasana, chin mudra, hand on heart | ✓ | – |  |
| s6_thiruvalluvar | White robes, beard, hair knot, writing on palm leaf, no mark | ✓ | – |  |
| s6_sambandar | Small child mid-dance, finger pointing up, cup in left hand | ✓ | – |  |
| s6_appar | Shaven head, vibhuti, rudraksha, hoe on shoulder, joined hands | ✓ | – |  |
| s6_avvaiyar | Stooped elder in white, walking stick, palm leaf | ✓ | – |  |
| s7_yashoda | Seated churning a tall pot with a rope churn | ✓ | – |  |
| s7_vennai_kannan | Crawling blue baby, butter on fingers, pot tipped over | ✓ | – |  |
| s7_gopi_pot | Pot balanced on her head | ✓ | – |  |
| s7_kaliya_krishna | Dancing on five dark hoods, holding the serpent's tail | ✓ | – |  |
| s7_govardhana_krishna | Hill held up on his left little finger, flute in right | ✓ | – |  |
| s7_gopi_shelter | Joined hands under the hill | ✓ | – |  |
| s7_cow_shelter | Cow under the hill | ✓ | – |  |
| s8_adi … s8_dhana | Each on a pink lotus with the arm count and emblems in rules R19–R26 | ✓ | – |  |
| s9_durga | Eight arms, trishula forward, riding a maned lion | ✓ | – |  |
| s9_lakshmi | Pink silk, two lotuses, coins pouring into a small pile | ✓ | – |  |
| s9_ganesha | Grey elephant head, right tusk broken, trunk to the modak, mouse at the peetam | ✓ | ✓ |  |
| s9_saraswati | White saree, veena across the lap, swan beside | ✓ | – |  |
| s9_kalasam | Brass kalasam, mango leaves, coconut, gold Amman face, on a rice mound | ✓ | – |  |
| s9_marapachi_raja / _rani | Red-brown wood figures with simple painted faces, dressed in silk | ✓ | – |  |

## 3. Sources

- Ashta Lakshmi arms, emblems and garment colours: [Wikipedia, Ashta Lakshmi](https://en.wikipedia.org/wiki/Ashta_Lakshmi). The left-to-right order follows the Ashtalakshmi Stotram (Adi, Dhanya, Dhairya, Gaja, Santana, Vijaya, Vidya, Dhana).
- Valli on Murugan's right, Deivanai on his left: [Wikipedia, Valli](https://en.wikipedia.org/wiki/Valli), [Subramaniya Swamy Temple, Tiruttani](https://en.wikipedia.org/wiki/Subramaniya_Swamy_Temple,_Tiruttani).
- Valli's millet field, raised platform and sling: [poetryinstone.in](https://poetryinstone.in/en/tag/valli/).
- Sambandar's pointing finger and cup: [Wikipedia, Sambandar](https://en.wikipedia.org/wiki/Sambandar), [Minneapolis Institute of Art](https://collections.artsmia.org/art/1374/child-shaiva-saint-sambandar-india).
- Appar's hoe: [Wikipedia, Appar](https://en.wikipedia.org/wiki/Appar).
- Andal's parrot in the left hand and side-tied hair: [Srivilliputhur temple notes, eSamskriti](https://esamskriti.com/e/Culture/Indian-Culture/About-Srivilliputhur-Temple,-Tamil-Nadu-1.aspx).
- Balarama fair-skinned in blue garments with plough and pestle: [Wikipedia, Balarama](https://en.wikipedia.org/wiki/Balarama).
- Vamana as a two-armed brahmachari with umbrella and water pot: [Wikipedia, Dasavatara shrine](https://en.wikipedia.org/wiki/Dasavatara_shrine), [LACMA](https://collections.lacma.org/node/246824).
- Thiruvalluvar's official portrait: [The News Minute](https://www.thenewsminute.com/tamil-nadu/portrait-thiruvalluvar-saffron-robes-cbse-textbook-receives-flak-tn-leaders-143863).
- Nammazhwar beneath the tamarind tree: [Wikipedia, Nammalvar](https://en.wikipedia.org/wiki/Nammalvar).
- Marapachi dolls on the top step, carved from red sanders: [Wikipedia, Marapachi Dolls](https://en.wikipedia.org/wiki/Marapachi_Dolls), [Wikipedia, Golu](https://en.wikipedia.org/wiki/Golu_(festival)).
- Kuthuvilakku parts and the annam finial: [Wikipedia, Nachiarkoil lamp](https://en.wikipedia.org/wiki/Nachiarkoil_lamp).
