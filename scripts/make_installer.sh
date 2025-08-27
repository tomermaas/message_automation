#!/usr/bin/env bash
set -euo pipefail

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller is required. Install it with 'pip install pyinstaller'." >&2
  exit 1
fi

if ! command -v makeself >/dev/null 2>&1; then
  echo "makeself is required. Install it via 'apt-get install -y makeself' or 'brew install makeself'." >&2
  exit 1
fi

# Ensure Python shared library is available for PyInstaller
PYTHON_LIB=$(python3 - <<'PYTHON'
import os, sysconfig
libdir = sysconfig.get_config_var('LIBDIR')
ldlib = sysconfig.get_config_var('LDLIBRARY')
path = os.path.join(libdir, ldlib) if libdir and ldlib else ''
# Some Python builds expose only a static library (e.g. .a). PyInstaller requires
# a shared library (.so, .dylib, .dll). Treat static libraries as missing.
ext = os.path.splitext(ldlib)[1] if ldlib else ''
if path and os.path.exists(path) and ext not in ('.a', '.lib'):
    print(path)
else:
    print('')
PYTHON
)

if [[ -z "$PYTHON_LIB" ]]; then
  echo "Python shared library not found. PyInstaller requires libpython for the current interpreter." >&2
  if command -v apt-get >/dev/null 2>&1; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "Attempting to install python${PY_VER}-dev..." >&2
    if command -v sudo >/dev/null 2>&1; then
      sudo apt-get update && sudo apt-get install -y "python${PY_VER}-dev" || sudo apt-get install -y python3-dev
    else
      apt-get update && apt-get install -y "python${PY_VER}-dev" || apt-get install -y python3-dev
    fi
  else
    echo "Please install the appropriate python development package (e.g. python3-dev) and retry." >&2
    exit 1
  fi
fi

pyinstaller build/message_automation.spec --clean

mkdir -p installer
makeself --nox11 dist/message_automation installer/message_automation.run "Message Automation Installer" ./message_automation

echo "Installer written to installer/message_automation.run"

