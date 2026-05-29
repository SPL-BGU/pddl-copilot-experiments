# design-diagrams

Three paper visualizations, sourced as Obsidian Excalidraw drawings.
This folder doubles as an Obsidian vault.

| Diagram | File | What it shows |
|---|---|---|
| 1 — Agent harness | [Excalidraw/agent-harness.md](Excalidraw/agent-harness.md) | Configuration space (model × condition × think × variant × task) and the two agent variants (`with-tools` vs `no-PDDL-tools`). |
| 2 — Experiment flow | [Excalidraw/experiment-flow.md](Excalidraw/experiment-flow.md) | End-to-end pipeline: cluster submit → vLLM self-deploy → MCP boot → ground-truth → per-cell eval loop → scoring → aggregation → sync. |
| 3 — Marketplace architecture | [Excalidraw/marketplace.md](Excalidraw/marketplace.md) | `pddl-copilot` marketplace: four plugins, plugin contract, stdio MCP transport, external planning/validation engines. |

## Editing

Open the folder as an Obsidian vault and edit the drawings directly.
The Obsidian Excalidraw plugin (Zsolt Viczián) stores each drawing as a
single `.md` file with the JSON embedded — readable in git, mergeable in
diffs.

## Exporting for the paper

The Excalidraw plugin exports PNG/SVG/PDF from each drawing:
- In Obsidian, open a drawing → command palette → `Excalidraw: Export image`.
- Or use the eye-icon → `Save as PNG/SVG/Excalidraw`.

Do not commit the exports — they're regenerable from the `.md` source.

## Maintenance

Update the drawings when the methodology drifts — they're snapshots, not
living documents. The authoritative spec stays in
[`../EXPERIMENTS_FLOW.md`](../EXPERIMENTS_FLOW.md).
