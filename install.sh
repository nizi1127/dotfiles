#!/usr/bin/env bash
# Dotfiles installer — runs automatically by VS Code Dev Containers
# (settings: dev.containers.dotfiles.repository / .targetPath / .installCommand)
# and works the same way on WSL hosts when invoked manually.
#
# Idempotent: safe to run repeatedly. Each block updates if present, installs if missing.

set -euo pipefail

SUPERPOWERS_DIR="${HOME}/.copilot/skills/superpowers-upstream"
PROMPTS_DIR="${HOME}/.vscode-server/data/User/prompts"

# Skills to expose as VS Code Copilot Chat slash-commands.
# Edit this list to taste.
SKILLS=(
  brainstorming
  test-driven-development
  systematic-debugging
  writing-plans
  executing-plans
  requesting-code-review
  verification-before-completion
)

log() { printf '\033[36m[dotfiles]\033[0m %s\n' "$*"; }

# 1. Clone or update the Superpowers upstream repo.
if [[ -d "${SUPERPOWERS_DIR}/.git" ]]; then
  log "Updating Superpowers at ${SUPERPOWERS_DIR}"
  git -C "${SUPERPOWERS_DIR}" pull --ff-only --quiet || log "  (pull failed, keeping local copy)"
else
  log "Cloning Superpowers into ${SUPERPOWERS_DIR}"
  mkdir -p "$(dirname "${SUPERPOWERS_DIR}")"
  git clone --depth 1 https://github.com/obra/superpowers "${SUPERPOWERS_DIR}"
fi

# 2. Symlink chosen skills into VS Code's user-prompt folder so Copilot Chat
#    surfaces them as `/skill-name` slash commands across every workspace.
mkdir -p "${PROMPTS_DIR}"
for skill in "${SKILLS[@]}"; do
  src="${SUPERPOWERS_DIR}/skills/${skill}/SKILL.md"
  dst="${PROMPTS_DIR}/${skill}.prompt.md"
  if [[ -f "${src}" ]]; then
    ln -sfn "${src}" "${dst}"
    log "  linked ${skill}"
  else
    log "  ! skipped ${skill} (not found in upstream)"
  fi
done

log "Done. ${#SKILLS[@]} skills processed."
