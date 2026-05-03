# AOAI Cost Skill — Install Guide

A self-contained skill that estimates Azure OpenAI cost from a free-form query
like `gpt41 gpt5mini input=779+1332 output=43+69 cost`.

## Contents

```
aoai-cost/
├── SKILL.md                   # skill manifest (auto-loaded by Copilot)
├── assets/pricing.json        # USD per 1M tokens, edit to update prices
└── scripts/aoai_cost.py       # the calculator
```

No third-party dependencies — only Python 3.10+ standard library.

## Requirements

- Python 3.10 or newer (`python --version`)
- VS Code with GitHub Copilot Chat (only needed for slash-command / chat usage;
  the script alone runs without it)

## Install (per machine)

Pick **one** scope. Folder name **must** be `aoai-cost`.

### A. Personal — works in every workspace (recommended)

Copy the entire `aoai-cost/` folder into one of these user-level paths:

| OS | Path |
|----|------|
| Windows | `%USERPROFILE%\.copilot\skills\aoai-cost\` |
| macOS / Linux | `~/.copilot/skills/aoai-cost/` |

Alternatives (any of these also work, pick whichever you already use):
`~/.agents/skills/aoai-cost/` or `~/.claude/skills/aoai-cost/`.

### B. Project-scoped — checked into a repo

Copy the folder to one of:

- `<repo>/.github/skills/aoai-cost/`
- `<repo>/.agents/skills/aoai-cost/`
- `<repo>/.claude/skills/aoai-cost/`

Anyone who clones the repo gets the skill.

## Quick install commands

### Windows (PowerShell)

```powershell
$dest = "$env:USERPROFILE\.copilot\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force ".\aoai-cost" $dest
```

### macOS / Linux (bash)

```bash
mkdir -p "$HOME/.copilot/skills"
cp -R ./aoai-cost "$HOME/.copilot/skills/"
```

## Verify

```powershell
python "$env:USERPROFILE\.copilot\skills\aoai-cost\scripts\aoai_cost.py" `
    "gpt41 input 2000 output 800 cost"
```

Expected: a table ending in `TOTAL: $10.4000 USD`.

In Copilot Chat, type `/` and you should see `aoai-cost` in the list. Or just
ask in natural language, e.g.

> gpt41 gpt5mini input=779+1332 output=43+69 cost

Copilot will auto-load the skill (because the description matches) and run
the calculator.

## Updating prices

Edit [assets/pricing.json](./assets/pricing.json). Format:

```json
"gpt-x.y": { "input": 1.25, "output": 10.00 }
```

Numbers are USD per 1,000,000 tokens, Global Standard deployment. Source:
<https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/>

Add new models or override regional rates as needed. Fuzzy match handles
short aliases automatically (`gpt41`, `41`, `GPT 4.1` all → `gpt-4.1`).

## Uninstall

Delete the `aoai-cost` folder from whichever location you installed it to.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/aoai-cost` doesn't appear in chat | Restart VS Code; verify folder path matches table above; check `SKILL.md` is at the folder root. |
| `ERROR: could not detect a known model` | Use a recognizable form: `gpt41`, `gpt-4.1`, `4.1`. Pure `41` is ambiguous and rejected. |
| Wrong price reported | Open [assets/pricing.json](./assets/pricing.json) and update the entry. |
| `python: command not found` | Install Python 3.10+; on Windows ensure it's on `PATH` (re-run installer with "Add Python to PATH"). |
