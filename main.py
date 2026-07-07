"""
PPT Generator — main entry point.

Usage:
  python main.py input.json [output.pptx] [--mode beauty|tradeoff]
  python main.py '{"topic":"...","brief":"...","audience":"..."}' [output.pptx] [--mode ...]
  echo '{"topic":"..."}' | python main.py [output.pptx] [--mode ...]
"""

import argparse
import json
import sys
import time

from parser import Slide, fallback_parse, parse
from prompt import call_llm
from renderer import render_pptx

# Pricing: (input_$/MTok, output_$/MTok)
# claude-sonnet-5 intro pricing valid through 2026-08-31
_RATES = {
    "beauty": (2.00, 10.00),
    "tradeoff": (1.00, 5.00),
}


def _cost(in_tok: int, out_tok: int, mode: str) -> float:
    r = _RATES.get(mode, _RATES["tradeoff"])
    return (in_tok * r[0] + out_tok * r[1]) / 1_000_000


def _generate(topic: str, brief: str, audience: str, mode: str, error_hint: str = ""):
    """Wrap call_llm, optionally injecting a parse-error hint into the brief."""
    full_brief = brief
    if error_hint:
        full_brief = (
            f"{brief}\n\n"
            f"[重要：上次输出解析失败，原因：{error_hint}。"
            f"请确保只输出纯合法 JSON，不含任何 markdown 或解释文字。]"
        )
    return call_llm(topic, full_brief, audience, mode=mode)


def main():
    ap = argparse.ArgumentParser(description="Generate a .pptx from a JSON description")
    ap.add_argument("input", nargs="?", help="JSON string, file path, or omit for stdin")
    ap.add_argument("output", nargs="?", default="output.pptx", help="Output .pptx path")
    ap.add_argument(
        "--mode",
        choices=["beauty", "tradeoff"],
        default="beauty",
        help="beauty = max quality (claude-sonnet-5); tradeoff = fast+cheap (claude-haiku-4-5)",
    )
    args = ap.parse_args()

    # ── Read input ──────────────────────────────────────────────────────────
    if args.input is None:
        raw = sys.stdin.read()
    elif args.input.lstrip().startswith("{"):
        raw = args.input
    else:
        with open(args.input, encoding="utf-8") as f:
            raw = f.read()

    inp = json.loads(raw)
    topic = inp.get("topic", "Untitled")
    brief = inp.get("brief", "")
    audience = inp.get("audience", "General audience")

    print(f"[PPTAgent] topic={topic!r}  mode={args.mode}")
    t0 = time.time()

    # ── Step 1: LLM call ────────────────────────────────────────────────────
    raw_text, in_tok, out_tok = _generate(topic, brief, audience, args.mode)

    # ── Step 2: Parse with one retry, then hard fallback ────────────────────
    ppt_data = None
    for attempt in range(2):
        try:
            ppt_data = parse(raw_text)
            break
        except Exception as exc:
            if attempt == 0:
                print(f"[PPTAgent] parse attempt 1 failed ({exc}), retrying…")
                raw_text2, in2, out2 = _generate(
                    topic, brief, audience, args.mode, error_hint=str(exc)
                )
                in_tok += in2
                out_tok += out2
                raw_text = raw_text2
            else:
                print(f"[PPTAgent] parse attempt 2 also failed ({exc}), using fallback")
                ppt_data = fallback_parse(topic, raw_text)

    # ── Step 3: Guarantee ≥ 25 slides ───────────────────────────────────────
    while len(ppt_data.slides) < 25:
        ppt_data.slides.append(
            Slide(layout="bullets", title="补充内容", bullets=["内容生成中，请稍后"])
        )

    # ── Step 4: Render ───────────────────────────────────────────────────────
    render_pptx(ppt_data, args.output)

    duration = time.time() - t0
    cost = _cost(in_tok, out_tok, args.mode)

    print(
        f"[PPTAgent] Done!  slides={len(ppt_data.slides)}"
        f"  tokens={in_tok}+{out_tok}"
        f"  cost=${cost:.4f}"
        f"  duration={duration:.1f}s"
        f"  output={args.output}"
    )


if __name__ == "__main__":
    main()
