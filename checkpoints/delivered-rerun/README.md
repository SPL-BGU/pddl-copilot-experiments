# checkpoints/delivered-rerun — backup of the delivered rerun corpus (Study 2, part 1)

The only git backup of `results/delivered-rerun/` (gitignored), the corpus the frozen
analysis (`delivered-rerun-analysis-frozen`, see `development/STATUS.md` "Pinned commits")
read out on 2026-10-09. Zipped 2026-10-10 from the laptop copy, which was checked
byte-identical (sha256 of every `trials.jsonl`) against the cluster originals.

One zip per model, each holding that model's cell folders with `trials.jsonl`,
`summary_*.json` and `single_task_*.json`:

| zip | cells |
|---|---|
| `Qwen3_5_9B_trials.zip` | 9B no-tools, 9B tools (plain + steered) |
| `gemma4_26b-a4b_trials.zip` | Gemma no-tools, Gemma tools (plain + steered), Gemma neutral 2x2 |
| `qwen3_6_35b_trials.zip` | 35B no-tools, 35B tools (plain + steered) |

## Restore

```bash
mkdir -p results/delivered-rerun
for z in checkpoints/delivered-rerun/*_trials.zip; do unzip -q -o "$z" -d results/delivered-rerun/; done
```

## sha256

```
4cdb52cc4c17e228b2443543890cb55f9b0d965c62d404ac6e159a6378dd475b  Qwen3_5_9B_trials.zip
03f2b52f843727defcfd782d33a6148f12f20bc4b57eb01ed0743ac5db3ef60b  gemma4_26b-a4b_trials.zip
4c4d5b8defe61b52e101ff60c0ba17756647a6c947ccb1bfa15f5ef095ab9be2  qwen3_6_35b_trials.zip
1ac1104697c0735a83587198c7b4fe03e47afc3026cc20f3810fa3b77aff8163  slurm_vllm_Qwen3_5_9B_off_no-tools_delivered-rerun/trials.jsonl
353c64b87272c63dbfcdbb7fdf63226735bee97bf49ba1e8257edfb68607e07f  slurm_vllm_Qwen3_5_9B_off_tools_all_minimal_delivered-rerun/trials.jsonl
3f300043cd1c1b14f0e06e4c0370a795c58f746b9f483449e3c34a84c8531a19  slurm_vllm_gemma4_26b-a4b_off_no-tools_delivered-rerun/trials.jsonl
48fbe7d7a8ccc4850515d92b8af45a6a7bcddec83f29d02c507bec0bd75cbe3d  slurm_vllm_gemma4_26b-a4b_off_tools_all_minimal_delivered-rerun/trials.jsonl
44f756345c589bb54f894bc0f1f5a197cab0a7fc6541fa05d9d454da99b2df71  slurm_vllm_gemma4_26b-a4b_off_tools_all_neutral_delivered-rerun-neutral/trials.jsonl
2087d18bf4e4cab927aee696e58f0db729fd40bf9d7dd73e52c63b7080290b5f  slurm_vllm_qwen3_6_35b_off_no-tools_delivered-rerun/trials.jsonl
6795e3508cc754e1d21edc025768121b90f657b1b97c455f6eef197144633a52  slurm_vllm_qwen3_6_35b_off_tools_all_minimal_delivered-rerun/trials.jsonl
```
