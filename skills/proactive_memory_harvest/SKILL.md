# Proactive Memory Harvest (Pre-Compact)

Trigger this skill when ANY of the following is true:
- The user types `/proactive_memory_harvest` explicitly
- The conversation is approaching context limits (long sessions, many tool calls)
- A multi-step task has just completed
- The user mentions "compact", "summarize", "wrap up", "save", or "before we lose this"

## Operating Mode Notice

The user runs in bypass-approvals mode. You will NOT be interrupted before
file writes. This means YOU must self-impose a review gate via the output
contract below — never write to /memories/ before printing the preview block
and waiting for the user's response on the SAME turn (do not auto-proceed
from preview to write within one turn unless the trigger phrase already
contained explicit consent like "harvest and save", "save now", "go ahead").

## Step 1 — Scan

Review the entire conversation so far. Identify candidates that would help a
FUTURE session and would otherwise be lost when context is compacted.

Sources to scan:
- Implementation decisions and the reasoning behind them
- Bug-fix root causes and the symptom→cause mapping
- Tool/command invocations that took >1 attempt to get right
- Architecture facts discovered from source code (not from speculation)
- User preferences expressed during the session
- Anti-patterns the user explicitly rejected

## Step 2 — Classify

Each candidate maps to exactly one scope:

| Scope | Path | Use for |
|---|---|---|
| user | /memories/<topic>.md | Personal coding preferences, cross-workspace patterns, lessons that apply beyond this repo |
| repo | /memories/repo/<topic>.md | Stable facts about THIS repo: conventions, build commands, helper contracts, architecture |
| session | /memories/session/<topic>.md | Temporary state to carry into the next turn/task; auto-cleared after conversation |

Reject candidates that are:
- Already covered by an existing memory file (check via `memory view` first)
- Trivially re-derivable from source code or function names
- One-off debugging steps with no reusable insight
- Speculative ("might be useful if...") — only verified facts

## Step 3 — Preview (MANDATORY before any write)

Print exactly this block, then STOP and wait for user input:

    ## Memory Harvest Preview
    
    Found N candidates. Existing files checked: [list].
    
    ### Proposed writes
    
    1. [scope] path/to/file.md — CREATE | UPDATE | APPEND
       Summary: <one-line description>
       Why: <why future sessions need this>
       Content preview:
       ```
       <first 5-10 lines of content>
       ```
    
    2. ...
    
    ### Skipped candidates
    - <candidate>: <reason skipped>
    
    Reply: `save all` | `save 1,3` | `edit N` | `skip` | `discard`

## Step 4 — Write (only after explicit user instruction)

On approval:
- Use the memory tool with `create` for new files, `str_replace` or `insert` for updates
- For each write, print: `📝 Saved: <path> — <one-line summary>`
- After all writes, print: `Done. N entries persisted. To undo any: memory delete <path>`

## Step 5 — Self-evaluation

After the harvest, briefly note:
- Any candidates that felt borderline (so the user can refine the rules)
- Topics that recurred enough to suggest a NEW skill rather than memory

## Anti-patterns to avoid

- Do NOT batch-write without preview, even in bypass mode. The preview IS the safety net.
- Do NOT create a new file when an existing one covers 80%+ of the topic — update instead.
- Do NOT capture session-specific debugging breadcrumbs as user-scope memory.
- Do NOT duplicate content already in /workspaces/*/.github/ files (those are version-controlled; memory is for things that don't belong in the repo).