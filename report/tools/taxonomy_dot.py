"""Генерация diags/taxonomy.dot по dataset.json (дерево ЛР1: корень → L1 → L2 → L3 → объекты)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
records = json.loads((ROOT / "1-dataset" / "dataset.json").read_text(encoding="utf-8"))["records"]
lines = ['digraph T {', 'rankdir=LR; nodesep=0.06; ranksep=0.55; splines=line;',
         'node [fontname="DejaVu Sans", fontsize=11, shape=box, style="rounded,filled", fillcolor="#ffffff", color="#7a1f3d", height=0.25, margin="0.06,0.02"];',
         'edge [color="#8a7d72", arrowhead=none];', 'root [label="Ликёры", fillcolor="#7a1f3d", fontcolor="white"];']
seen: dict = {}
fills = {1: "#f3e3e8", 2: "#f7ead9", 3: "#e9f0fa"}
for r in records:
    t = r["taste"]
    path = [t["l1"], t["l2"], t["l3"]]
    parent = "root"
    for depth in range(3):
        key = tuple(path[: depth + 1])
        node = seen.get(key) or f"n{len(seen)}"
        if key not in seen:
            seen[key] = node
            lines.append(f'{node} [label="{path[depth]}", fillcolor="{fills[depth + 1]}"];')
            lines.append(f"{parent} -> {node};")
        parent = node
    lines.append(f'{r["id"]} [label="{r["id"]} {r["name"]}", shape=plaintext, style="", fontsize=10];')
    lines.append(f'{parent} -> {r["id"]} [style=dashed];')
lines.append("}")
(Path(__file__).resolve().parents[1] / "diags" / "taxonomy.dot").write_text("\n".join(lines), encoding="utf-8")
