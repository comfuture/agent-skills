#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/install.sh [--dry-run] [--no-agents] [skill ...]

Copy managed skills from this repository into $CODEX_HOME/skills, defaulting to
$HOME/.codex/skills. With no skill arguments, installs the skill names listed in
managed-skills.txt. If that file is missing, falls back to every immediate
repository directory that contains SKILL.md.

Options:
  --dry-run     Print planned writes without changing files.
  --no-agents   Do not copy repository AGENTS.md to $CODEX_HOME/AGENTS.md.
  -h, --help    Show this help.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"
dry_run=0
copy_agents=1
skills=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=1
      ;;
    --no-agents)
      copy_agents=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        skills+=("$1")
        shift
      done
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      skills+=("$1")
      ;;
  esac
  shift
done

discover_skills() {
  local skill_dir skill_name

  if [[ -f "$repo_root/managed-skills.txt" ]]; then
    while IFS= read -r skill_name || [[ -n "$skill_name" ]]; do
      [[ -z "$skill_name" || "$skill_name" == \#* ]] && continue
      skills+=("$skill_name")
    done < "$repo_root/managed-skills.txt"
    return
  fi

  while IFS= read -r skill_dir; do
    skill_name="$(basename "$(dirname "$skill_dir")")"
    [[ "$skill_name" == .* ]] && continue
    skills+=("$skill_name")
  done < <(find "$repo_root" -mindepth 2 -maxdepth 2 -name SKILL.md -type f | sort)
}

validate_skill_name() {
  local skill="$1"
  if [[ "$skill" == .* || "$skill" == */* ]]; then
    echo "Refusing suspicious skill name: $skill" >&2
    exit 2
  fi
}

sync_dir() {
  local src="$1"
  local dst="$2"

  if [[ ! -d "$src" ]]; then
    echo "Missing source directory: $src" >&2
    exit 1
  fi

  if [[ "$dry_run" -eq 1 ]]; then
    echo "Would sync $src/ -> $dst/"
    return
  fi

  mkdir -p "$dst"
  rsync -a --delete "$src/" "$dst/"
}

if [[ "${#skills[@]}" -eq 0 ]]; then
  discover_skills
fi

if [[ "$copy_agents" -eq 1 && -f "$repo_root/AGENTS.md" ]]; then
  if [[ "$dry_run" -eq 1 ]]; then
    echo "Would install $repo_root/AGENTS.md -> $codex_home/AGENTS.md"
  else
    mkdir -p "$codex_home"
    install -m 0644 "$repo_root/AGENTS.md" "$codex_home/AGENTS.md"
  fi
fi

if [[ "$dry_run" -eq 0 ]]; then
  mkdir -p "$codex_home/skills"
fi

for skill in "${skills[@]}"; do
  validate_skill_name "$skill"
  sync_dir "$repo_root/$skill" "$codex_home/skills/$skill"
done
