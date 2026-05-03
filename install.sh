#!/usr/bin/env bash
# Dotfiles installer — runs automatically by VS Code Dev Containers
# (settings: dev.containers.dotfiles.repository / .targetPath / .installCommand)
# and works the same way on WSL hosts when invoked manually.
#
# Idempotent: safe to run repeatedly. Each block updates if present, installs if missing.

set -euo pipefail

SUPERPOWERS_DIR="${HOME}/.copilot/skills/superpowers-upstream"
PERSONAL_SKILLS_DIR="${HOME}/.copilot/skills"
DOTFILES_SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"
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

# 3. Sync version-controlled personal skills from the dotfiles repo into
#    ~/.copilot/skills/ as symlinks so they're discoverable in fresh containers.
if [[ -d "${DOTFILES_SKILLS_DIR}" ]]; then
  mkdir -p "${PERSONAL_SKILLS_DIR}"
  for dir in "${DOTFILES_SKILLS_DIR}"/*/; do
    [[ -d "${dir}" ]] || continue
    name="$(basename "${dir}")"
    target="${PERSONAL_SKILLS_DIR}/${name}"
    # Replace if already a symlink (refresh), skip if it's a real dir from another source
    if [[ ! -e "${target}" || -L "${target}" ]]; then
      ln -sfn "${dir%/}" "${target}"
      log "  synced personal skill ${name} from dotfiles"
    fi
  done
fi

# 4. Clean up dangling symlinks under ~/.copilot/skills/ (skills removed from
#    dotfiles repo).
for link in "${PERSONAL_SKILLS_DIR}"/*; do
  if [[ -L "${link}" && ! -e "${link}" ]]; then
    rm -f "${link}"
    log "  pruned dangling link $(basename "${link}")"
  fi
done

# 5. Symlink any PERSONAL skills (every dir under ~/.copilot/skills/ with a
#    SKILL.md) into the prompts folder. Excludes superpowers-upstream.
personal_count=0
if [[ -d "${PERSONAL_SKILLS_DIR}" ]]; then
  for dir in "${PERSONAL_SKILLS_DIR}"/*/; do
    [[ -d "${dir}" ]] || continue
    name="$(basename "${dir}")"
    [[ "${name}" == "superpowers-upstream" ]] && continue
    src="${dir}SKILL.md"
    [[ -f "${src}" ]] || continue
    dst="${PROMPTS_DIR}/${name}.prompt.md"
    ln -sfn "${src}" "${dst}"
    log "  linked personal ${name}"
    personal_count=$((personal_count + 1))
  done
fi

# 6. Prune dangling .prompt.md symlinks (skills removed from disk).
for link in "${PROMPTS_DIR}"/*.prompt.md; do
  if [[ -L "${link}" && ! -e "${link}" ]]; then
    rm -f "${link}"
    log "  pruned dangling prompt $(basename "${link}")"
  fi
done

log "Done. ${#SKILLS[@]} upstream + ${personal_count} personal skills processed."
