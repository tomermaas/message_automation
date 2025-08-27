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

pyinstaller build/message_automation.spec --clean

mkdir -p installer
makeself --nox11 dist/message_automation installer/message_automation.run "Message Automation Installer" ./message_automation

echo "Installer written to installer/message_automation.run"

