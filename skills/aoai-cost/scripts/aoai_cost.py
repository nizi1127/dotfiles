"""Azure OpenAI cost estimator.

Usage (flag form):
    python aoai_cost.py --model gpt-4.1 --input-tokens 1500 --output-tokens 500 \
        --calls-per-request 3 --requests 1000

Usage (free-form, defaults to 1 call/request and 1000 requests):
    python aoai_cost.py "gpt41 input 2000 output 800 cost?"
    python aoai_cost.py gpt5.2 in 1500 out 500
    python aoai_cost.py "gpt41 i=2000 o=800 calls=3 requests=5000"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

PRICING_PATH = Path(__file__).resolve().parent.parent / "assets" / "pricing.json"


def load_pricing(path: Path = PRICING_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)["models"]


def cost_per_call(model_price: dict, input_tokens: int, output_tokens: int) -> tuple[float, float]:
    in_cost = input_tokens / 1_000_000 * model_price["input"]
    out_cost = output_tokens / 1_000_000 * model_price["output"]
    return in_cost, out_cost


def _normalize(name: str) -> str:
    """Lowercase + strip non-alphanumerics. 'GPT 4.1' -> 'gpt41', '41' -> '41'.

    Also folds common typos: 'got' -> 'gpt'.
    """
    n = re.sub(r"[^a-z0-9]", "", name.lower())
    # Common typo: 'got' -> 'gpt' at start of token.
    if n.startswith("got"):
        n = "gpt" + n[3:]
    return n


def resolve_model(query: str, pricing: dict) -> tuple[str, list[str]]:
    """Resolve a fuzzy model query to a canonical key.

    Returns (matched_key, candidates). If exactly one candidate matches,
    matched_key is that candidate. Otherwise matched_key is "" and candidates
    contains the suggested alternatives (possibly empty).
    """
    if query in pricing:
        return query, [query]

    nq = _normalize(query)
    if not nq:
        return "", []

    norm_map = {_normalize(k): k for k in pricing}

    # 1) exact normalized match
    if nq in norm_map:
        return norm_map[nq], [norm_map[nq]]

    # 2) prefix match (e.g. "gpt5" -> "gpt5", "gpt5mini", ...). If only one, use it.
    prefix = [orig for nk, orig in norm_map.items() if nk.startswith(nq)]
    if len(prefix) == 1:
        return prefix[0], prefix

    # 3) substring match (e.g. "41" -> "gpt41", "gpt41mini", ...)
    substr = [orig for nk, orig in norm_map.items() if nq in nk]

    # Prefer the shortest candidate when query is contained — usually the base model.
    # e.g. "41" contained in {"gpt41","gpt41mini","gpt41nano"} -> pick "gpt-4.1".
    candidates = prefix or substr
    if candidates:
        # Sort by (normalized length, name) so the most "base" model wins for auto-pick.
        candidates_sorted = sorted(candidates, key=lambda k: (len(_normalize(k)), k))
        if len(candidates_sorted) == 1:
            return candidates_sorted[0], candidates_sorted
        # Auto-pick if the shortest is strictly shorter than the next one.
        a, b = candidates_sorted[0], candidates_sorted[1]
        if len(_normalize(a)) < len(_normalize(b)):
            return a, candidates_sorted
        # Ambiguous: return suggestions only.
        return "", candidates_sorted

    # 4) fallback: difflib similarity ranking
    ranked = sorted(
        pricing.keys(),
        key=lambda k: SequenceMatcher(None, nq, _normalize(k)).ratio(),
        reverse=True,
    )
    suggestions = [k for k in ranked
                   if SequenceMatcher(None, nq, _normalize(k)).ratio() >= 0.5][:5]
    return "", suggestions


def parse_freeform(text: str, pricing: dict) -> dict:
    """Parse a natural-ish query like 'gpt41 input 2000 output 800 cost?'.

    Returns a dict with keys: model, input_tokens, output_tokens,
    calls_per_request, requests. Missing optional keys default to
    calls_per_request=1, requests=1000. Raises ValueError on failure.
    """
    t = text.lower()

    # A single value term: 1500, 1_500, 1,500, 1.5k, 2m
    TERM = r"\d[\d_,]*(?:\.\d+)?[kKmM]?"
    # An arithmetic expression: TERM (([+\-*/]) TERM)* — supports `779+1332`, `100*3`, `1k+500`.
    EXPR = rf"{TERM}(?:\s*[+\-*/]\s*{TERM})*"

    def to_int(s: str) -> int:
        s = s.replace(",", "").replace("_", "")
        mult = 1
        if s and s[-1] in "kK":
            mult, s = 1_000, s[:-1]
        elif s and s[-1] in "mM":
            mult, s = 1_000_000, s[:-1]
        return int(float(s) * mult)

    def eval_expr(expr: str) -> int:
        """Evaluate a restricted arithmetic expression of TERMs and + - * /."""
        # Split on operators while keeping them.
        parts = re.split(r"(\s*[+\-*/]\s*)", expr)
        # Convert each TERM, keep operators verbatim.
        py = ""
        for i, part in enumerate(parts):
            if i % 2 == 0:
                py += str(to_int(part.strip()))
            else:
                py += part.strip()
        # Safe: only digits and + - * / remain.
        if not re.fullmatch(r"[\d+\-*/ ]+", py):
            raise ValueError(f"unsupported expression: {expr!r}")
        return int(eval(py, {"__builtins__": {}}, {}))  # noqa: S307 — sanitized

    def grab_kw(keywords: list[str]) -> int | None:
        for kw in keywords:
            # `input 2000`, `input=779+1332`, `input: 1k+500`
            m = re.search(rf"\b{kw}\b\s*[:=]?\s*({EXPR})", t)
            if m:
                return eval_expr(m.group(1))
        return None

    input_tokens = grab_kw(["input", "in", "i", "input_tokens", "input-tokens", "x"])
    output_tokens = grab_kw(["output", "out", "o", "output_tokens", "output-tokens", "y"])
    calls = grab_kw(["calls", "call", "calls_per_request", "calls-per-request", "fanout", "fan-out", "n"])
    requests_ = grab_kw(["requests", "request", "reqs", "req", "r"])

    # Detect model: try every token-ish candidate against fuzzy resolver.
    # Tokens: alphanumeric + dots + dashes.
    tokens = re.findall(r"[a-z0-9][a-z0-9.\-]*", t)
    # Skip pure-number tokens that are clearly token counts (1500, 1k, 2m).
    # But keep version-like dotted numbers (4.1, 5.2) — those are model identifiers.
    def _is_value_token(tok: str) -> bool:
        if re.fullmatch(r"\d+(?:[._,]\d+)*[kKmM]", tok):
            return True  # 1k, 2.5k, 1m
        if re.fullmatch(r"\d[\d_,]*", tok):
            return True  # 1500, 1_500, 1,500
        return False
    tokens = [tok for tok in tokens if not _is_value_token(tok)]
    # Skip parameter keywords so 'i', 'o', 'in', 'out' etc. don't match models like 'o3'.
    KEYWORDS = {
        "input", "output", "in", "out", "i", "o", "x", "y", "n", "r",
        "input_tokens", "output_tokens", "input-tokens", "output-tokens",
        "calls", "call", "calls_per_request", "calls-per-request",
        "fanout", "fan-out",
        "requests", "request", "reqs", "req",
        "cost", "tokens", "token", "per", "and", "with", "for", "the",
    }
    tokens = [tok for tok in tokens if tok not in KEYWORDS]

    model_keys: list[str] = []
    seen: set[str] = set()
    # Preserve original token order in the query, but try longer tokens first
    # so 'gpt-4.1' beats 'gpt' when both are present.
    ordered = sorted(enumerate(tokens), key=lambda iv: (-len(iv[1]), iv[0]))
    for _, tok in ordered:
        resolved, _c = resolve_model(tok, pricing)
        if resolved and resolved not in seen:
            seen.add(resolved)
            model_keys.append(resolved)

    if not model_keys:
        raise ValueError(f"could not detect a known model in: {text!r}")
    # Re-sort by first appearance in original text for stable display order.
    model_keys.sort(key=lambda mk: min(
        (i for i, tok in enumerate(tokens)
         if resolve_model(tok, pricing)[0] == mk),
        default=10**9,
    ))

    if input_tokens is None:
        raise ValueError("could not find input token count (try 'input 2000' or 'i=2000')")
    if output_tokens is None:
        raise ValueError("could not find output token count (try 'output 800' or 'o=800')")

    return {
        "models": model_keys,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "calls_per_request": calls if calls is not None else 1,
        "requests": requests_ if requests_ is not None else 1000,
    }


def _looks_like_freeform(argv: list[str]) -> bool:
    """True if no --flag present and at least one arg given."""
    return bool(argv) and not any(a.startswith("--") or a.startswith("-") and len(a) > 1 and not a[1].isdigit()
                                  for a in argv)


def _print_report(model: str, mp: dict, input_tokens: int, output_tokens: int,
                  calls_per_request: int, requests: int) -> float:
    in_per_call, out_per_call = cost_per_call(mp, input_tokens, output_tokens)
    per_call = in_per_call + out_per_call
    per_request = per_call * calls_per_request
    total = per_request * requests
    total_in = in_per_call * calls_per_request * requests
    total_out = out_per_call * calls_per_request * requests

    print(f"Model:               {model}")
    print(f"  input  $/1M tok:   ${mp['input']:.4f}")
    print(f"  output $/1M tok:   ${mp['output']:.4f}")
    print(f"Per AOAI call:       ${per_call:.6f}  (in ${in_per_call:.6f} + out ${out_per_call:.6f})")
    print(f"Calls per request:   {calls_per_request}")
    print(f"Per product request: ${per_request:.6f}")
    print(f"Requests estimated:  {requests:,}")
    print("-" * 40)
    print(f"Total input cost:    ${total_in:,.4f}")
    print(f"Total output cost:   ${total_out:,.4f}")
    print(f"TOTAL:               ${total:,.4f} USD")
    return total


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)

    # Free-form mode: `python aoai_cost.py "gpt41 gpt5.2 input=779+1332 output=47+376"`
    if _looks_like_freeform(raw):
        pricing = load_pricing(PRICING_PATH)
        text = " ".join(raw)
        try:
            parsed = parse_freeform(text, pricing)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print("Hint: try `python aoai_cost.py \"gpt-4.1 input 2000 output 800\"` "
                  "or use --model/--input-tokens/--output-tokens flags.", file=sys.stderr)
            return 2

        models = parsed["models"]
        totals: list[tuple[str, float]] = []
        for i, m in enumerate(models):
            if i > 0:
                print()
                print("=" * 40)
            total = _print_report(
                m, pricing[m],
                parsed["input_tokens"], parsed["output_tokens"],
                parsed["calls_per_request"], parsed["requests"],
            )
            totals.append((m, total))

        if len(totals) > 1:
            print()
            print("=" * 40)
            print("Comparison (TOTAL USD):")
            width = max(len(m) for m, _ in totals)
            for m, t in sorted(totals, key=lambda x: x[1]):
                print(f"  {m:<{width}}  ${t:,.4f}")
        return 0

    p = argparse.ArgumentParser(description="Estimate Azure OpenAI cost.")
    p.add_argument("--model", required=True, help="Model name, must exist in pricing.json")
    p.add_argument("--input-tokens", type=int, required=True, help="Avg input tokens per AOAI call (x)")
    p.add_argument("--output-tokens", type=int, required=True, help="Avg output tokens per AOAI call (y)")
    p.add_argument("--calls-per-request", type=int, default=1,
                   help="AOAI calls fanned out per product API request (default 1)")
    p.add_argument("--requests", type=int, default=1000,
                   help="Total product API requests to estimate (default 1000)")
    p.add_argument("--pricing", type=Path, default=PRICING_PATH, help="Path to pricing.json")
    p.add_argument("--strict", action="store_true",
                   help="Disable fuzzy matching; require exact model key.")
    args = p.parse_args(raw)

    pricing = load_pricing(args.pricing)

    if args.strict:
        if args.model not in pricing:
            print(f"ERROR: model '{args.model}' not found in {args.pricing}", file=sys.stderr)
            print(f"Available: {', '.join(sorted(pricing))}", file=sys.stderr)
            return 2
        resolved = args.model
    else:
        resolved, candidates = resolve_model(args.model, pricing)
        if not resolved:
            print(f"ERROR: model '{args.model}' did not match any entry in {args.pricing}",
                  file=sys.stderr)
            if candidates:
                print(f"Did you mean: {', '.join(candidates)}?", file=sys.stderr)
            else:
                print(f"Available: {', '.join(sorted(pricing))}", file=sys.stderr)
            return 2
        if resolved != args.model:
            print(f"[fuzzy] '{args.model}' -> '{resolved}'", file=sys.stderr)

    _print_report(
        resolved, pricing[resolved],
        args.input_tokens, args.output_tokens,
        args.calls_per_request, args.requests,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
