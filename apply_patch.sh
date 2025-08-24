#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/Kidum/message_automation"
cd "$ROOT"

echo ">> Working in: $ROOT"

# 1) Ensure data/sample/.gitkeep
if [[ ! -f "data/sample/.gitkeep" ]]; then
  mkdir -p "data/sample"
  : > "data/sample/.gitkeep"
  echo "created: data/sample/.gitkeep"
else
  echo "exists : data/sample/.gitkeep"
fi

# 2) Ensure .env.example
if [[ ! -f ".env" ]]; then
  cat > .env<< 'EOF'
LMS_BASE_URL=https://kidum-me.com
LMS_API_BASE_URL=https://lmsapi.kidum-me.com
PLAYWRIGHT_HEADLESS=true
EOF
  echo "created: .env"
else
  echo "exists : .env (left unchanged)"
fi

# 3) Fill requirements.txt only if empty (no overwrite if it already has content)
touch requirements.txt
if [[ ! -s requirements.txt ]]; then
  cat > requirements.txt << 'EOF'
PySide6>=6.7
playwright>=1.46
jinja2>=3.1
python-dotenv>=1.0
pytest>=8.2
pyinstaller>=6.10
EOF
  echo "updated: requirements.txt (was empty)"
else
  echo "exists : requirements.txt (left unchanged)"
fi

# 4) Rename spec file if present (use git mv when repo is clean)
SRC="build/kidum_scout.spec"
DST="build/message_automation.spec"
if [[ -f "$SRC" && ! -e "$DST" ]]; then
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # try to use git mv for a tidy history
    git mv "$SRC" "$DST" || mv "$SRC" "$DST"
  else
    mv "$SRC" "$DST"
  fi
  echo "renamed: $SRC -> $DST"
else
  echo "skip  : spec rename (source missing or target exists)"
fi

# Stage changes so you can commit in one go
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git add -A
  echo ">> Staged changes. Commit with:"
  echo "   git commit -m 'Add .gitkeep/.env.example, populate requirements, rename spec file'"
fi

echo "Done."

