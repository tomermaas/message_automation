#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./create_layout.sh                # creates ./kidum-scout under current dir
#   ./create_layout.sh /path/to/dir   # creates structure at /path/to/dir
#
# Notes:
# - Creates directories and empty files ONLY if missing.
# - Never overwrites existing files.

ROOT="${1:-$PWD}"

echo "Creating project skeleton at: $ROOT"

make_dir() {
  local d="$1"
  if [[ ! -d "$d" ]]; then
    mkdir -p "$d"
    echo "dir:   $d"
  else
    echo "exist: $d"
  fi
}

make_file() {
  local f="$1"
  if [[ ! -e "$f" ]]; then
    mkdir -p "$(dirname "$f")"
    : > "$f"   # create empty file
    echo "file:  $f"
  else
    echo "exist: $f"
  fi
}

# Directories
dirs=(
  "$ROOT/app"
  "$ROOT/ui"
  "$ROOT/automation"
  "$ROOT/automation/extractors"
  "$ROOT/logic"
  "$ROOT/logic/templates"
  "$ROOT/data/sample"
  "$ROOT/tests"
  "$ROOT/scripts"
  "$ROOT/build"
  "$ROOT/.github/workflows"
)

for d in "${dirs[@]}"; do make_dir "$d"; done

# Files
files=(
  "$ROOT/app/__init__.py"
  "$ROOT/app/main.py"
  "$ROOT/app/config.py"
  "$ROOT/app/logging_conf.py"

  "$ROOT/ui/__init__.py"
  "$ROOT/ui/login_view.py"
  "$ROOT/ui/home_view.py"

  "$ROOT/automation/__init__.py"
  "$ROOT/automation/browser.py"
  "$ROOT/automation/extractors/__init__.py"
  "$ROOT/automation/extractors/students.py"
  "$ROOT/automation/extractors/courses.py"

  "$ROOT/logic/__init__.py"
  "$ROOT/logic/rules.py"
  "$ROOT/logic/messages.py"
  "$ROOT/logic/templates/student_message.j2"

  "$ROOT/tests/test_smoke.py"

  "$ROOT/scripts/postinstall_playwright.py"

  "$ROOT/build/kidum_scout.spec"

  "$ROOT/.env.example"
  "$ROOT/.gitignore"
  "$ROOT/requirements.txt"
  "$ROOT/README.md"

  "$ROOT/.github/workflows/build.yml"
)

for f in "${files[@]}"; do make_file "$f"; done

echo "Done."