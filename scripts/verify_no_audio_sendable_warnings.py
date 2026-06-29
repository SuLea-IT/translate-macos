#!/usr/bin/env python3
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
build_root = Path('/tmp/livebuddy_sendable_check')
if build_root.exists():
    shutil.rmtree(build_root)
source_root = build_root / 'src' / 'LiveBuddy'
(source_root.parent).mkdir(parents=True, exist_ok=True)
shutil.copytree(root / 'LiveBuddy', source_root)

for swift_file in source_root.rglob('*.swift'):
    text = swift_file.read_text()
    marker = '\n#Preview {'
    index = text.find(marker)
    if index != -1:
        swift_file.write_text(text[:index].rstrip() + '\n')

sdk = subprocess.check_output(['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
sources = sorted(str(path) for path in source_root.rglob('*.swift'))
command = [
    '/usr/bin/swiftc',
    '-swift-version', '5',
    '-target', 'arm64-apple-macosx14.6',
    '-sdk', sdk,
    '-framework', 'SwiftUI',
    '-framework', 'AppKit',
    '-framework', 'AVFoundation',
    '-framework', 'ScreenCaptureKit',
    '-framework', 'Security',
    '-framework', 'Carbon',
    '-framework', 'UniformTypeIdentifiers',
    '-framework', 'CoreAudio',
    '-framework', 'Combine',
    *sources,
    '-o', str(build_root / 'LiveBuddy'),
]
result = subprocess.run(command, text=True, capture_output=True)
combined = result.stdout + result.stderr
if result.returncode != 0:
    print(combined)
    sys.exit(result.returncode)

blocked_patterns = [
    "main actor-isolated property 'audioPlayer'",
    "non-Sendable type 'PCM16AudioPlayer?'",
    'SendableClosureCaptures',
]
found = [pattern for pattern in blocked_patterns if pattern in combined]
if found:
    print('Audio Sendable warning verification failed:')
    for pattern in found:
        print(f'- {pattern}')
    sys.exit(1)
print('Audio Sendable warning verification passed')
