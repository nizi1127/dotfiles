# dotfiles

Personal dev-environment bootstrap. Wires the [obra/superpowers](https://github.com/obra/superpowers)
skills library into VS Code Copilot Chat as user-scoped prompts, so they work
across every workspace and every dev container — without touching any project's
`.devcontainer.json`.

## What it does

`install.sh`:
1. Clones (or `git pull`s) `obra/superpowers` to `~/.copilot/skills/superpowers-upstream`.
2. Symlinks selected `SKILL.md` files into `~/.vscode-server/data/User/prompts/<name>.prompt.md`
   so Copilot Chat exposes them as `/<name>` slash commands.

Idempotent — safe to run on every container start.

## One-time setup

1. Push this folder to GitHub as `<your-user>/dotfiles`.
2. In **VS Code user settings** (host machine *and* each WSL distro), set:

   | Setting | Value |
   |---|---|
   | `dev.containers.dotfiles.repository` | `<your-user>/dotfiles` |
   | `dev.containers.dotfiles.targetPath` | `~/dotfiles` |
   | `dev.containers.dotfiles.installCommand` | `~/dotfiles/install.sh` |

3. Rebuild / reopen any dev container — skills install automatically.
4. On the WSL host (outside containers), run once: `bash ~/dotfiles/install.sh`.

## Customising the skill list

Edit the `SKILLS=( ... )` array in `install.sh`. Re-run to apply.

## Updating

- Inside a container: rebuild, or `bash ~/dotfiles/install.sh`.
- On WSL: `git -C ~/dotfiles pull && bash ~/dotfiles/install.sh`.

## Notes

- `~/.copilot/skills/` is the convention used by Copilot **CLI**; storing the
  upstream clone there keeps it discoverable for both Chat (via symlinks) and
  CLI (if you later install it).
- VS Code Settings Sync will sync the resulting `.prompt.md` files between
  machines if "Prompts" is enabled — but the symlink targets must exist on each
  host, which is exactly what this installer guarantees.
