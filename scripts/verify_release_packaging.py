#!/usr/bin/env python3
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

package_script = ROOT / 'scripts' / 'package_release.sh'
install_note = ROOT / 'packaging' / 'INSTALL.txt'
release_workflow = ROOT / '.github' / 'workflows' / 'release.yml'
readme = ROOT / 'README.md'

require(package_script.exists(), 'scripts/package_release.sh is missing')
if package_script.exists():
    text = package_script.read_text()
    require(os.access(package_script, os.X_OK), 'scripts/package_release.sh must be executable')
    for token in ['xcodebuild', 'swiftc', 'codesign --force --sign -', 'hdiutil create', 'hdiutil verify', 'zip -qry -X', 'INSTALL.txt', 'shasum -a 256']:
        require(token in text, f'package script missing {token!r}')

require(install_note.exists(), 'packaging/INSTALL.txt is missing')
if install_note.exists():
    text = install_note.read_text()
    for phrase in ['Right-click', 'Open', 'unidentified developer', 'Applications']:
        require(phrase in text, f'INSTALL.txt missing {phrase!r}')

if release_workflow.exists():
    text = release_workflow.read_text()
    for token in ['workflow_dispatch', 'tags:', 'v*', 'scripts/package_release.sh', 'gh release create', 'LiveTranslateBuddy-macOS-arm64.dmg', 'LiveTranslateBuddy-macOS-arm64.zip']:
        require(token in text, f'release workflow missing {token!r}')

if readme.exists():
    text = readme.read_text()
    if 'GitHub Releases' in text or 'right-click' in text:
        require('Right-click' in text or 'right-click' in text, 'README should mention right-click Open for free builds')

if errors:
    for error in errors:
        print(f'ERROR: {error}')
    sys.exit(1)
print('Release packaging verification passed')
