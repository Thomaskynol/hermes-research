#!/usr/bin/env python3
"""Replay `_select_hits` over a saved corpus — no searches, no fetching.

    python replay_selection.py corpus.json [--seed N] [--out selected.json]

`corpus.json` is a list of {source, url, title, raw_content} (the shape in
`corpus_collected.json` produced by run_trace, or the fixture in
`fixtures/selection_demo.json`).

`--seed N` shuffles a COPY of the corpus with a local `random.Random(N)`
before selection. This mirrors the ordering effect of the unseeded
`random.shuffle` at `researcher.py:869` in site-packages so the order effect
can be demonstrated — the seed controls ONLY this replay ordering. It does
NOT control retrievers, concurrency, chunking, or the model.

No seed = input order. Output: per-doc verdicts (kept/dropped_dupe/
dropped_cut) plus the sha256 of the selected URL list on stdout.
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, "/opt/data/deep_research_outputs/gpt_researcher")

from vast_local_retriever import Hit, _select_hits  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("corpus", help="JSON list of source/url/title/raw_content")
    ap.add_argument("--seed", type=int, default=None,
                    help="shuffle a copy with random.Random(seed) first; "
                         "controls replay order ONLY")
    ap.add_argument("--out", default=None, help="write verdicts JSON here")
    args = ap.parse_args()

    docs = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    hits = [Hit(url=d.get("url", ""), title=d.get("title", ""),
                raw_content=d.get("raw_content", ""),
                source=d.get("source", "")) for d in docs]

    if args.seed is not None:
        rng = random.Random(args.seed)  # local instance; global random untouched
        rng.shuffle(hits)

    selected = _select_hits(hits)
    kept_ids = {id(h) for h in selected}
    seen: set[str] = set()
    verdicts = []
    for h in hits:
        if not h.url or h.url in seen:
            verdict = "dropped_dupe"
        elif id(h) in kept_ids:
            verdict = "kept"
        else:
            verdict = "dropped_cut"
        if h.url and h.url not in seen:
            seen.add(h.url)
        verdicts.append({"source": h.source, "url": h.url,
                         "title": h.title, "verdict": verdict})

    digest = hashlib.sha256(
        "\n".join(h.url for h in selected).encode()).hexdigest()
    result = {"seed": args.seed, "input_docs": len(hits),
              "kept": len(selected), "sha256_selected_urls": digest,
              "verdicts": verdicts}
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    print(json.dumps({"kept": len(selected), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
