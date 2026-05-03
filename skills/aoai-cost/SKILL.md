---
name: aoai-cost
description: 'Calculate Azure OpenAI (AOAI) cost for a product line. Use when the user asks about AOAI cost, OpenAI pricing, token cost estimation, cost per N requests, or how much GPT-4.1 / GPT-5 / o-series will cost. Handles the case where one product API request fans out to multiple AOAI calls with given input/output token usage and a model name.'
argument-hint: '<model> <input_tokens> <output_tokens> [--calls-per-request N] [--requests 1000]'
---

# AOAI Cost Estimation

## When to Use
- User wants to estimate Azure OpenAI cost for a product line.
- One product-side API request triggers one or more AOAI requests.
- User provides: model name `m`, average input tokens `x`, average output tokens `y`, optionally calls-per-request and total request count.

## Inputs
- `model`: e.g. `gpt-4.1`, `gpt-4.1-mini`, `gpt-4o`, `gpt-4o-mini`, `gpt-5`, `gpt-5-mini`, `o3`, `o4-mini`. See [pricing.json](./assets/pricing.json). Fuzzy match is supported — `gpt41`, `41`, `GPT 4.1` all resolve to `gpt-4.1`. Use `--strict` to disable.
- `input_tokens` (x): average input tokens per single AOAI call.
- `output_tokens` (y): average output tokens per single AOAI call.
- `calls_per_request`: how many AOAI calls one product request fans out to (default `1`).
- `requests`: total product-side request count to estimate (default `1000`).

## Procedure
1. Load the pricing table from [./assets/pricing.json](./assets/pricing.json). Prices are USD per 1M tokens.
   - If the model is missing or the user is unsure about current rates, ask the user to confirm or update the file. **Do not fabricate prices.**
2. Run the calculator. Two equivalent forms — prefer the free-form for short user phrasings:
   - **Free-form** (defaults: `calls_per_request=1`, `requests=1000`):
     ```
     python ./scripts/aoai_cost.py "gpt41 input 2000 output 800 cost?"
     python ./scripts/aoai_cost.py "gpt5.2 in 1500 out 500 calls=3 requests=10000"
     ```
   - **Flag form**:
     ```
     python ./scripts/aoai_cost.py --model <m> --input-tokens <x> --output-tokens <y> \
         --calls-per-request <n> --requests <r>
     ```
   See [aoai_cost.py](./scripts/aoai_cost.py).
3. Report:
   - Cost per single AOAI call
   - Cost per single product request (× `calls_per_request`)
   - Total cost for `requests` product requests (default 1000)
   - Breakdown of input vs output cost

## Formula
$$
\text{cost} = \text{requests} \times \text{calls\_per\_request} \times \left( \frac{x}{10^6} \cdot p_\text{in} + \frac{y}{10^6} \cdot p_\text{out} \right)
$$

where $p_\text{in}, p_\text{out}$ are USD per 1M tokens for the chosen model.

## Notes
- Prices in [pricing.json](./assets/pricing.json) are best-effort defaults. Always verify against the latest [Azure OpenAI pricing page](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/) before quoting numbers externally.
- Cached input tokens, batch discounts, and fine-tuned model surcharges are **not** modeled. Add them manually if needed.
