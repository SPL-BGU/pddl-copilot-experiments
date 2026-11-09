# KCL VAL on the Claude solve plans (C1 method)

VAL: VAL: The PDDL+ plan validation tool Version 4: Validates continuous effects, events and processes. Authors: Derek Long, Richard Howey, Stephen Cresswell and Maria Fox https:://github/KCL-Planning/VAL; sha256 `44a07d6d3b2917c7c3df8e3932a3b895a8062b4e0f5fa0343f9f1ad409c4a9fe`.

Solve rows read: 1,100; distinct graded plans: 771. Harness verdict = live pyval through the plugin. A plan counts as handled when both gave a verdict and VAL read as many steps as were sent (after adding brackets to bare `name arg` lines, where needed).

## Plans: VAL against pyval (Wilson 95%)

| group | distinct plans | agree / handled | of which VAL read with brackets added | pyval valid (handled) | disagree: pyval rejects the fixture's own upper-case names | disagree: other | VAL cannot handle | pyval error shape (graded a failure) |
|---|---|---|---|---|---|---|---|---|
| all plans | 771 | 734 / 745 (98.52%, [97.38, 99.17]) | 18 | 293 | 11 | 0 | 5 | 21 |
| arm: tool arm | 219 | 219 / 219 (100.00%, [98.28, 100.00]) | 0 | 209 | 0 | 0 | 0 | 0 |
| arm: unaided | 578 | 541 / 552 (98.01%, [96.47, 98.88]) | 18 | 110 | 11 | 0 | 5 | 21 |
| track: classical | 396 | 364 / 373 (97.59%, [95.48, 98.73]) | 18 | 152 | 9 | 0 | 5 | 18 |
| track: numeric | 375 | 370 / 372 (99.46%, [98.06, 99.85]) | 0 | 141 | 2 | 0 | 0 | 3 |
| Sonnet 4.6 | unaided | canonical | 205 | 187 / 196 (95.41%, [91.50, 97.57]) | 8 | 43 | 9 | 0 | 2 | 7 |
| Sonnet 4.6 | unaided | renamed | 206 | 190 / 190 (100.00%, [98.02, 100.00]) | 10 | 48 | 0 | 0 | 2 | 14 |
| Sonnet 4.6 | tool arm | canonical | 106 | 106 / 106 (100.00%, [96.50, 100.00]) | 0 | 101 | 0 | 0 | 0 | 0 |
| Haiku 4.5 | unaided | canonical | 99 | 95 / 98 (96.94%, [91.38, 98.95]) | 0 | 22 | 3 | 0 | 1 | 0 |
| Haiku 4.5 | unaided | renamed | 99 | 99 / 99 (100.00%, [96.26, 100.00]) | 0 | 19 | 0 | 0 | 0 | 0 |
| Haiku 4.5 | tool arm | canonical | 105 | 105 / 105 (100.00%, [96.47, 100.00]) | 0 | 102 | 0 | 0 | 0 | 0 |
| Haiku 4.5 | tool arm | renamed | 102 | 102 / 102 (100.00%, [96.37, 100.00]) | 0 | 100 | 0 | 0 | 0 | 0 |

Classes over all plans: VAL cannot handle (crash_rc-11) 5; agree 718; agree, with brackets added 16; pyval error shape (prose, not a plan) 21; pyval rejects names written in the fixture's own upper case (valid in lower case) 11.

## Row level

| cell | rows | answer at the 16,384-char cap (not rebuilt) | pyval regrade = stored `success` | online-graded rows VAL handled | VAL regrade = stored | stored fail → VAL success | stored success → VAL fail | delivered plans (tool arm) | pyval = overlay | VAL = overlay |
|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | unaided | canonical | 300 | 2 | 298 / 298 | 271 / 280 | 259 / 271 | 12 | 0 | 0 | 0 / 0 | 0 / 0 |
| Sonnet 4.6 | unaided | renamed | 300 | 2 | 298 / 298 | 253 / 271 | 253 / 253 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| Sonnet 4.6 | tool arm | canonical | 100 | 0 | 100 / 100 | 100 / 100 | 100 / 100 | 0 | 0 | 100 | 100 / 100 | 100 / 100 |
| Haiku 4.5 | unaided | canonical | 100 | 1 | 99 / 99 | 98 / 99 | 95 / 98 | 3 | 0 | 0 | 0 / 0 | 0 / 0 |
| Haiku 4.5 | unaided | renamed | 100 | 1 | 99 / 99 | 99 / 99 | 99 / 99 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| Haiku 4.5 | tool arm | canonical | 100 | 0 | 100 / 100 | 100 / 100 | 100 / 100 | 0 | 0 | 98 | 98 / 98 | 98 / 98 |
| Haiku 4.5 | tool arm | renamed | 100 | 0 | 100 / 100 | 100 / 100 | 100 / 100 | 0 | 0 | 99 | 99 / 99 | 99 / 99 |

## Every plan where VAL and pyval do not agree, or one of them gave no verdict

### VAL cannot handle (crash_rc-11)

- canonical gripper p04 `e089ddf29fb3` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL cannot_handle `crash_rc-11` (as sent); plan: `(pick robot2 ball1 room2 rgripper2) | (pick robot2 ball3 room2 lgripper2) | (move robot2 room2 room1) | (drop robot2 ball3 room1) | (pick robot2 ball2 room1 lgr`
- canonical gripper p05 `1dc0a77b003f` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL cannot_handle `crash_rc-11` (as sent); plan: `(pick robot2 ball3 room1 rgripper2) | (pick robot2 ball4 room1 lgripper2) | (pick robot3 ball3 room1 rgripper3) | (move robot2 room1 room3) | (drop robot2 ball3`
- renamed gripper p04 `153d1b444c68` (Sonnet 4.6 | unaided | renamed): pyval invalid `STRUCTURE_ERROR`, VAL cannot_handle `crash_rc-11` (as sent); plan: `(collect carrier2 parcel1 bay2 righthand2) | (collect carrier2 parcel3 bay2 lefthand2) | (walk carrier2 bay2 bay1) | (deposit carrier2 parcel3 bay1) | (collect `
- renamed gripper p04 `1dd251e32ee7` (Sonnet 4.6 | unaided | renamed): pyval invalid `STRUCTURE_ERROR`, VAL cannot_handle `crash_rc-11` (as sent); plan: `(collect carrier2 parcel1 bay2 righthand2) | (collect carrier2 parcel3 bay2 lefthand2) | (walk carrier2 bay2 bay1) | (collect carrier2 parcel2 bay1 righthand2) `
- canonical barman p01 `0c406afe32f2` (Haiku 4.5 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL cannot_handle `crash_rc-11` (as sent); plan: `(grasp left shot1) | (fill_shot shot1 ingredient1 left right dispenser1) | (grasp right shaker1) | (pour_shot_to_clean_shaker shot1 ingredient1 shaker1 left l0 `

### pyval error shape (prose, not a plan)

- canonical depots p04 `a9ca5ea75a8e` (Sonnet 4.6 | unaided | canonical): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze the goal:- crate0 on pallet2 (distributor0)- crate1 on pallet1 (depot1)- crate2 on crate3- crate3 on crate1So the stack at depot1 should be: pal`
- canonical depots p04 `03c5dfb1f9f1` (Sonnet 4.6 | unaided | canonical): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me trace through this carefully.`
- canonical tpp p04 `558e90ebd4c9` (Sonnet 4.6 | unaided | canonical): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: `]Let me analyze this problem carefully.}Let me think through this step by step.I need to analyze the domain and problem carefully.The goal is:- stored goods1 le`
- canonical depot p01 `4b591cee076e` (Sonnet 4.6 | unaided | canonical): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` I need to analyze the initial and goal states carefully.`
- canonical tpp p04 `388af4b7593d` (Sonnet 4.6 | unaided | canonical): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: `]Let me analyze this problem carefully.}Let me think through this step by step.I need to analyze the levels and what needs to happen:- stored goods1 level1 (cur`
- canonical depots p03 `4e7766a4f40d` (Sonnet 4.6 | unaided | canonical): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me trace through this step by step.`
- canonical barman p01 `fd0425381512` (Sonnet 4.6 | unaided | canonical): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me work through this step by step.`
- renamed depots p02 `42feba446b41` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze this problem.`
- renamed zenotravel p04 `7f707d4728af` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze this problem carefully.`
- renamed zenotravel p01 `feb017e565d3` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze this problem.`
- renamed depots p01 `d615a093a1d3` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze this problem carefully.`
- renamed pogo_stick p04 `74b1072d1e50` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze what's needed:`
- renamed depot p03 `6950608c0edf` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: `]`
- renamed tpp p05 `c942c856fc5d` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: `];} Let me analyze this problem carefully.}]`
- renamed depots p04 `26638e884b38` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze this problem carefully.`
- renamed tpp p05 `309f8dda596c` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: `]`
- renamed blocksworld p04 `2441ddd05ff0` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze the initial state and goal state.`
- renamed depots p05 `c8413c74fa29` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze this problem carefully.`
- renamed depots p02 `8c1f23a983b7` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` Let me analyze this problem carefully.`
- renamed depots p05 `65dcdf1adc0d` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: `]`
- renamed satellite p05 `2f713a2daa19` (Sonnet 4.6 | unaided | renamed): pyval error ``, VAL cannot_handle `not_read_as_sent` (not read); plan: ` I need to analyze this carefully.`

### pyval rejects names written in the fixture's own upper case (valid in lower case)

- canonical satellite p03 `38257d58dc30` (Haiku 4.5 | unaided | canonical; Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(switch_on instrument0 satellite0) | (turn_to satellite0 Star0 GroundStation1) | (calibrate satellite0 instrument0 Star0) | (turn_to satellite0 Phenomenon2 Star`
- canonical pogo_stick p02 `9e846e8f90fa` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(CRAFT_PLANK ) | (CRAFT_PLANK ) | (CRAFT_PLANK ) | (CRAFT_TREE_TAP cell21) | (TP_TO crafting_table cell22) | (PLACE_TREE_TAP cell22) | (CRAFT_WOODEN_POGO cell22`
- canonical satellite p04 `4f9ad7792548` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(turn_to satellite0 Star2 Phenomenon6) | (switch_on instrument0 satellite0) | (calibrate satellite0 instrument0 Star2) | (turn_to satellite0 Planet3 Star2) | (t`
- canonical satellite p05 `f8d1f4891c86` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(turn_to satellite0 Star2 Star1) | (switch_on instrument1 satellite0) | (calibrate satellite0 instrument1 Star2) | (turn_to satellite0 Planet3 Star2) | (take_im`
- canonical satellite p02 `a480a7bf5e7b` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(turn_to satellite0 GroundStation1 Star0) | (switch_on instrument0 satellite0) | (calibrate satellite0 instrument0 GroundStation1) | (turn_to satellite0 Phenome`
- canonical satellite p05 `2a32aa691896` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(switch_on instrument0 satellite0) | (calibrate satellite0 instrument0 Star1) | (turn_to satellite0 Planet3 Star1) | (take_image satellite0 Planet3 instrument0 `
- canonical satellite p05 `bb162a754dcc` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (with brackets added), pyval in lower case: valid; plan: `turn_to satellite0 Star2 Star1 | switch_on instrument1 satellite0 | calibrate satellite0 instrument1 Star2 | turn_to satellite0 Planet3 Star2 | take_image satel`
- canonical satellite p04 `f74333929933` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (with brackets added), pyval in lower case: valid; plan: `turn_to satellite0 Star2 Phenomenon6 | switch_on instrument0 satellite0 | calibrate satellite0 instrument0 Star2 | turn_to satellite0 Phenomenon6 Star2 | take_i`
- canonical pogo_stick p05 `5059fd12e708` (Sonnet 4.6 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(CRAFT_STICK ) | (CRAFT_STICK ) | (CRAFT_PLANK ) | (CRAFT_TREE_TAP cell22) | (TP_TO crafting_table cell15) | (PLACE_TREE_TAP cell15) | (TP_TO cell15 cell22) | (`
- canonical satellite p04 `0eb387367c72` (Haiku 4.5 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(turn_to satellite0 Star2 Phenomenon6) | (switch_on instrument0 satellite0) | (calibrate satellite0 instrument0 Star2) | (turn_to satellite0 Planet3 Star2) | (t`
- canonical satellite p05 `74ea2a51665b` (Haiku 4.5 | unaided | canonical): pyval invalid `STRUCTURE_ERROR`, VAL valid `plan_valid` (as sent), pyval in lower case: valid; plan: `(switch_on instrument8 satellite2) | (turn_to satellite2 Star1 Planet3) | (calibrate satellite2 instrument8 Star1) | (turn_to satellite2 Planet3 Star1) | (take_`

## Post hoc: unaided solve, renamed − canonical, stored grade vs VAL grade (T7 method)

VAL grade = the online grade with VAL in pyval's place, on rows where VAL read every plan the grader sent; other rows keep the stored grade.

| cell | n pairs | reference % | comparison % | Delta (pp) | governing 90% CI | governed by | 90% domain bootstrap | half-width | TOST p | verdict at +/-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 4.6 unaided solve, stored grade | 300 | 28.7 | 28.3 | -0.33 | [-10.59, +9.93] | domain (k=20) | [-9.67, +9.00] | 10.26 | 0.221 | criterion not met (unresolved) |
| Sonnet 4.6 unaided solve, VAL grade | 300 | 32.7 | 28.3 | -4.33 | [-14.38, +5.71] | domain (k=20) | [-13.67, +4.67] | 10.05 | 0.455 | criterion not met (unresolved) |
| Haiku 4.5 unaided solve, stored grade | 100 | 22.0 | 19.0 | -3.00 | [-12.14, +6.14] | domain (k=20) | [-12.00, +5.00] | 9.14 | 0.355 | criterion not met (unresolved) |
| Haiku 4.5 unaided solve, VAL grade | 100 | 25.0 | 19.0 | -6.00 | [-17.25, +5.25] | domain (k=20) | [-17.00, +4.00] | 11.25 | 0.560 | criterion not met (unresolved) |

