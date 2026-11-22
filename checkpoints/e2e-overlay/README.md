# checkpoints/e2e-overlay — the end-to-end overlay and the pooled table

The overlay is the regrade of every stored final answer (`tools/e2e_regrade.py`). It
lives in `results/derived/e2e_overlay/`, which git does not track, so these zips are
its backup. `.claude/skills/analyzer/scripts/e2e_pooled.py` reads that folder and writes
the pooled table (`pooled_e2e_table.{md,csv}`), the one source for every per-cell
delivered figure (see `development/NUMBERS.md`, "Single-tool suite — per-cell figures").

## What each zip holds

Each `<corpus>_overlay.zip` holds one folder, `<corpus>/`, with one `*.e2e.jsonl` per
cell. Unzip it into `results/derived/e2e_overlay/`.

| zip | holds | note |
|---|---|---|
| `sweep5v2-live_overlay.zip` | 20 cells of the open-model main sweep | the paper's open-model cells |
| `sweep6-live_overlay.zip` | 20 cells, the renamed (anonymised) twin | |
| `iss024d-e2e-live_overlay.zip` | 5 cells of the full-response rerun | a separate replication, never "the sweep5v2 cells resolved" |
| `decoupled-rollup_overlay.zip` | 8 cells of the decoupled-budget control | never pooled with the main sweep |
| `ntster-h4-live_overlay.zip` | 6 cells of the nt-ster H4 run | see `../ntster-h4-live/README.md` |
| `haiku-frontier_overlay.zip` | Haiku 4.5: 4 cells (both corpora, both arms) | 07-17 files; refresh below |
| `sonnet-frontier_overlay.zip` | Sonnet 4.6: 3 cells | 07-17 files; refresh below |
| `frontier-with-tools-probe_overlay.zip` | 3 cells of the June with-tools probe | kept for the table rebuild |
| `sweep7_overlay.zip` | 3 cells of the discarded BF16 35B run | **never quoted**; kept for the table rebuild |
| `derived_reports.zip` | the 07-17 pooled table and the iss024d parity report | refresh below |

Before quoting any figure from these, check `development/NUMBERS.md`.

**sweep7 rows are never quoted.** sweep7 was discarded entirely (decision of
2026-09-18 in `development/paper_notes_discussions.md`, "Q3, BF16-35B with-tools
control"): no BF16 number enters the paper. Its overlay stays here only because the
pooled table has a sweep7 block, and the table cannot be rebuilt row for row without it.
The same goes for the June with-tools probe.

## The two pooled tables: 456 and 460 rows

- `derived_reports.zip` holds the **2026-07-17** table. Its CSV has 456 data rows (count
  the lines yourself, or run the refresh script below in check mode: it prints the count
  and the rows per corpus). The CHANGELOG entry of 2026-07-17 ("ISS-024(d) endgame")
  records the same 456.
- The table `NUMBERS.md` cites is the **2026-09-12** one, 460 rows. It adds the
  `*-budget64k` rows of the frontier budget probe (CHANGELOG 2026-09-12: "The probe rows
  appear as their own `*-budget64k` run-tagged block"). It exists only on Omer's laptop
  until the refresh below is run.
- The handoff of 2026-11-09 (decision 16) records that a rebuild without the sweep7 and
  probe overlays gives 442 rows, not 460. That is why both are kept.

How the 07-17 table was checked (2026-11-09): the `*_overlay.zip` files here were
unzipped into a temp folder outside the repo and `e2e_pooled.py --overlay <tmp> --out
<tmp>` was run on it. Without `ntster-h4-live` the rebuilt CSV is byte-identical to the
one in `derived_reports.zip`, and a per-corpus count of that CSV gives the sweep7 block
18 rows and the probe block 13. The nt-ster run (2026-08-29) is newer than the 07-17
table, so that table never held its rows. With `ntster-h4-live` unzipped too, the
rebuild has that run's rows on top and matches neither table. Whether the 09-12 table
held them is not checked yet: the check mode of the refresh script prints its rows per
corpus on the laptop.

## Restore

```bash
mkdir -p results/derived/e2e_overlay
for z in checkpoints/e2e-overlay/*_overlay.zip; do
    unzip -q -o "$z" -d results/derived/e2e_overlay/
done
```

To rebuild the 07-17 table from these, leave `ntster-h4-live_overlay.zip` out and run
`python3 .claude/skills/analyzer/scripts/e2e_pooled.py` (it writes into the overlay
folder, over any table already there).

`derived_reports.zip` today (07-17 layout) holds flat names: put
`pooled_e2e_table.{md,csv}` in `results/derived/e2e_overlay/` and
`iss024d_parity_report.md` in `results/derived/`. After the refresh below, its entries
carry their path under `results/derived/`, so the restore is one command:
`unzip -q -o checkpoints/e2e-overlay/derived_reports.zip -d results/derived/`.

## Refresh to the 09-12 files (Omer, on the laptop)

Decision 16 asks for three refreshed zips here and a new `checkpoints/frontier/` set.
The inputs exist only on the laptop, so a script builds them there:

- `haiku-frontier_overlay.zip` and `sonnet-frontier_overlay.zip`: the 09-12 overlay
  files, which add `sweep5v2-budget64k` and `sweep5v2-with-tools-budget64k` per tier.
- `derived_reports.zip`: the 09-12 pooled table, the iss024d parity report, and
  `results/derived/budget_probe/readout_{sonnet,haiku}.json`.
- `checkpoints/frontier/<tier>-frontier_<cell>.zip`: one zip per raw frontier cell
  that git does not track (Haiku `sweep6`, the with-tools cells, the four
  `*-budget64k` folders). Unzip into `results/`.

From the main checkout:

```bash
# 1. Check only: lists missing inputs and the plan, writes nothing.
python3 tools/checkpoints/refresh_frontier_overlays.py
# 2. Build into a scratch folder and look at it.
python3 tools/checkpoints/refresh_frontier_overlays.py --write --out /tmp/ck-refresh
# 3. Build into checkpoints/ (replaces the three old zips, so it needs --force).
python3 tools/checkpoints/refresh_frontier_overlays.py --write --force
```

The script only reads `results/`. If any input is missing it builds nothing. It will
not replace a zip without `--force`, and it stops if a zip is over GitHub's 100 MB
limit. Entries are sorted and carry fixed permissions and the file's time in UTC
(`--fixed-time` stamps them all 1980-01-01 instead), so the same files give the same
sha256. In check mode it also prints the pooled CSV's row count per corpus. On the
laptop the total should read 460; the sweep7 and probe lines show what a rebuild
without them would lose, which checks the 442 note above. It prints a sha256 block
at the end. Paste it below, and into a new `checkpoints/frontier/README.md`.

## sha256 (2026-07-17 zips, before the refresh)

```
1aff83994d8a73d74d20f83cdb40deedda6f0837be11f632e145946bad51e6b3  decoupled-rollup_overlay.zip
fce64d593894771661733c203d196e8b25a283b46c2825567cddb730cd9748a1  derived_reports.zip
85536cb8207a6b6a22e6ec9b8b6e5457787b1d61a1bfd85d9caef1ebef6fe4e4  frontier-with-tools-probe_overlay.zip
abedaf15257cf2e27b2f49fa41a132fae9a7dd1c0523968f3f9c085622f9213f  haiku-frontier_overlay.zip
05fe6666af939e4b506459f7d5abe8bf5499e81ec231859d7702c0ceaa2aa4b3  iss024d-e2e-live_overlay.zip
93a76b2bc750749191416c1a72accb14ddf5ad9d8cb65ef38bb65c30adc2cd1b  ntster-h4-live_overlay.zip
73457ea1eeaa14d8ddea1706f90d4b1bcc32666452f6e2e314ec4d3e65605702  sonnet-frontier_overlay.zip
8af478182cc3e7ce0afdbc4033c5d8f6b49dccc9456862db504f316b8654ff8e  sweep5v2-live_overlay.zip
cb0c1bf9c5f25752657ece1e2a0c2226027f65e8283e873bc5d4bb4c3bf8f36d  sweep6-live_overlay.zip
b5cc095296bb5c4bbf6d457b65a5de015f977b73bca812176b11084449de7624  sweep7_overlay.zip
```

`ntster-h4-live_overlay.zip` is also pinned in `../ntster-h4-live/README.md`; it does
not change in the refresh.
