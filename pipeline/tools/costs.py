"""Rebuild the measured table in COSTS.md from runs.jsonl (between the generated markers)."""

from __future__ import annotations

import json
from collections import defaultdict

from ..common import ROOT, RUNS_LOG

START, END = "<!-- generated:start -->", "<!-- generated:end -->"


def table() -> str:
    rows: dict[tuple[str, str, str], dict] = defaultdict(lambda: {"ok": 0, "fail": 0, "lat": [], "price": 0.0,
                                                                  "priced": False})
    for line in RUNS_LOG.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "stage" not in e:
            continue
        r = rows[(e["stage"], e["provider"], e["model"])]
        if e["status"] == "ok":
            r["ok"] += 1
            r["lat"].append(e["latency_s"])
        else:
            r["fail"] += 1
        if e.get("list_price_usd") is not None:
            r["price"] += e["list_price_usd"]
            r["priced"] = True
    out = ["| Stage | Provider | Model | OK calls | Failed / retried | Mean latency (s) | Total time (s) | GPU min | List-price equivalent (USD) | Real spend |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    grand = 0.0
    for (stage, provider, model), r in sorted(rows.items()):
        mean = sum(r["lat"]) / len(r["lat"]) if r["lat"] else 0
        price = f"{r['price']:.4f}" if r["priced"] else ("0 (local)" if provider == "local" else "n/a")
        grand += r["price"]
        out.append(f"| {stage} | {provider} | {model} | {r['ok']} | {r['fail']} | {mean:.1f} | {sum(r['lat']):.1f} | "
                   f"{'0 (CPU)' if provider == 'local' else '0'} | {price} | $0 |")
    out.append(f"\nList-price total for every logged call: **${grand:.4f}**. Real spend: **$0** (free tiers and a CPU laptop).")
    return "\n".join(out)


def run(quiet: bool = False) -> None:
    path = ROOT / "COSTS.md"
    text = path.read_text(encoding="utf-8") if path.exists() else f"# Costs\n\n{START}\n{END}\n"
    a, b = text.index(START) + len(START), text.index(END)
    path.write_text(text[:a] + "\n" + table() + "\n" + text[b:], encoding="utf-8")
    if not quiet:
        print("COSTS.md updated from runs.jsonl")
