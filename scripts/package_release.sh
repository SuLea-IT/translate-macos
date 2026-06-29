#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="${APP_NAME:-Live Translate Buddy}"
EXECUTABLE_NAME="LiveBuddy"
BUNDLE_ID="${BUNDLE_ID:-com.sulea.translate-macos.LiveBuddy}"
VERSION="${VERSION:-$(git -C "$ROOT_DIR" describe --tags --always --dirty 2>/dev/null || echo 0.0.0)}"
RELEASE_DIR="${RELEASE_DIR:-$ROOT_DIR/releases}"
BUILD_ROOT="${BUILD_ROOT:-/tmp/livebuddy_release_build}"
APP_PATH="$RELEASE_DIR/$APP_NAME.app"
ZIP_PATH="$RELEASE_DIR/LiveTranslateBuddy-macOS-arm64.zip"
DMG_PATH="$RELEASE_DIR/LiveTranslateBuddy-macOS-arm64.dmg"
CHECKSUM_PATH="$RELEASE_DIR/LiveTranslateBuddy-macOS-arm64.sha256"
ENTITLEMENTS="$ROOT_DIR/LiveBuddy/LiveBuddy.entitlements"
ICON_DIR="$ROOT_DIR/LiveBuddy/Assets.xcassets/AppIcon.appiconset"
INSTALL_NOTE="$ROOT_DIR/packaging/INSTALL.txt"

log() { printf '[package] %s\n' "$*"; }
fail() { printf '[package] ERROR: %s\n' "$*" >&2; exit 1; }
require_tool() { command -v "$1" >/dev/null 2>&1 || fail "Required tool not found: $1"; }

require_tool /usr/bin/codesign
require_tool /usr/bin/iconutil
require_tool /usr/bin/hdiutil
require_tool /usr/bin/zip
require_tool /usr/bin/swiftc
[ -f "$ENTITLEMENTS" ] || fail "Missing entitlements: $ENTITLEMENTS"
[ -f "$INSTALL_NOTE" ] || fail "Missing install note: $INSTALL_NOTE"

rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT" "$RELEASE_DIR"

build_with_xcodebuild() {
  log "Building with xcodebuild"
  require_tool /usr/bin/xcodebuild
  local derived="$BUILD_ROOT/DerivedData"
  /usr/bin/xcodebuild build \
    -project "$ROOT_DIR/LiveBuddy.xcodeproj" \
    -scheme LiveBuddy \
    -configuration Release \
    -destination 'generic/platform=macOS' \
    -derivedDataPath "$derived" \
    CODE_SIGNING_ALLOWED=NO
  local built_app
  built_app="$(find "$derived/Build/Products" -path "*/Release/LiveBuddy.app" -type d | head -n 1)"
  [ -n "$built_app" ] || fail "xcodebuild did not produce LiveBuddy.app"
  rm -rf "$APP_PATH"
  cp -R "$built_app" "$APP_PATH"
}

strip_previews_for_swiftc() {
  local source_dir="$1"
  python3 - "$source_dir" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for p in root.rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
}

make_icns() {
  local out_icns="$1"
  local iconset="$BUILD_ROOT/AppIcon.iconset"
  rm -rf "$iconset"
  mkdir -p "$iconset"
  cp "$ICON_DIR/16-mac.png" "$iconset/icon_16x16.png"
  cp "$ICON_DIR/32-mac.png" "$iconset/icon_16x16@2x.png"
  cp "$ICON_DIR/32-mac 1.png" "$iconset/icon_32x32.png"
  cp "$ICON_DIR/64-mac.png" "$iconset/icon_32x32@2x.png"
  cp "$ICON_DIR/128-mac.png" "$iconset/icon_128x128.png"
  cp "$ICON_DIR/256-mac.png" "$iconset/icon_128x128@2x.png"
  cp "$ICON_DIR/256-mac 1.png" "$iconset/icon_256x256.png"
  cp "$ICON_DIR/512-mac.png" "$iconset/icon_256x256@2x.png"
  cp "$ICON_DIR/512-mac 1.png" "$iconset/icon_512x512.png"
  cp "$ICON_DIR/1024-mac.png" "$iconset/icon_512x512@2x.png"
  /usr/bin/iconutil -c icns "$iconset" -o "$out_icns"
}

build_with_swiftc() {
  log "Building with swiftc fallback"
  local src="$BUILD_ROOT/src"
  mkdir -p "$src"
  cp -R "$ROOT_DIR/LiveBuddy" "$src/LiveBuddy"
  strip_previews_for_swiftc "$src/LiveBuddy"
  mkdir -p "$BUILD_ROOT/bin"
  /usr/bin/swiftc \
    -swift-version 5 \
    -target arm64-apple-macosx14.6 \
    -sdk "$(/usr/bin/xcrun --sdk macosx --show-sdk-path)" \
    -framework SwiftUI -framework AppKit -framework AVFoundation -framework ScreenCaptureKit -framework Security -framework Carbon -framework UniformTypeIdentifiers -framework CoreAudio -framework Combine \
    $(find "$src/LiveBuddy" -name '*.swift' | sort) \
    -o "$BUILD_ROOT/bin/$EXECUTABLE_NAME"
  rm -rf "$APP_PATH"
  mkdir -p "$APP_PATH/Contents/MacOS" "$APP_PATH/Contents/Resources"
  cp "$BUILD_ROOT/bin/$EXECUTABLE_NAME" "$APP_PATH/Contents/MacOS/$EXECUTABLE_NAME"
  make_icns "$APP_PATH/Contents/Resources/AppIcon.icns"
  cat > "$APP_PATH/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>zh_CN</string>
    <key>CFBundleExecutable</key>
    <string>$EXECUTABLE_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.utilities</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Live Translate Buddy needs microphone access to translate live speech.</string>
    <key>NSScreenCaptureUsageDescription</key>
    <string>Live Translate Buddy needs screen recording access to capture system audio for live translation.</string>
</dict>
</plist>
PLIST
}

if [ "${FORCE_SWIFTC:-0}" = "1" ]; then
  build_with_swiftc
elif /usr/bin/xcode-select -p 2>/dev/null | grep -q '/Applications/Xcode.app/Contents/Developer' && [ -x /usr/bin/xcodebuild ]; then
  build_with_xcodebuild
else
  build_with_swiftc
fi

mkdir -p "$APP_PATH/Contents/Resources"
if [ ! -f "$APP_PATH/Contents/Resources/AppIcon.icns" ]; then
  make_icns "$APP_PATH/Contents/Resources/AppIcon.icns"
fi
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $BUNDLE_ID" "$APP_PATH/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $APP_NAME" "$APP_PATH/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$APP_PATH/Contents/Info.plist" 2>/dev/null || true
chmod +x "$APP_PATH/Contents/MacOS/$EXECUTABLE_NAME"
find "$APP_PATH" -name '._*' -delete
/usr/bin/xattr -cr "$APP_PATH" 2>/dev/null || true
log "Ad-hoc signing app"
/usr/bin/codesign --force --sign - --entitlements "$ENTITLEMENTS" "$APP_PATH"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$APP_PATH"

rm -f "$ZIP_PATH" "$DMG_PATH" "$CHECKSUM_PATH"
log "Creating clean ZIP"
(
  cd "$RELEASE_DIR"
  /usr/bin/zip -qry -X "$(basename "$ZIP_PATH")" "$(basename "$APP_PATH")" -x '*/._*' '__MACOSX/*'
)
if /usr/bin/zipinfo -1 "$ZIP_PATH" | grep -E '(^|/)\._|^__MACOSX/' >/dev/null; then
  fail "ZIP contains AppleDouble metadata"
fi

log "Creating DMG"
DMG_STAGING="$BUILD_ROOT/dmg"
rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "$APP_PATH" "$DMG_STAGING/$APP_NAME.app"
ln -s /Applications "$DMG_STAGING/Applications"
cp "$INSTALL_NOTE" "$DMG_STAGING/INSTALL.txt"
/usr/bin/hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_STAGING" -ov -format UDZO "$DMG_PATH" >/dev/null
/usr/bin/hdiutil verify "$DMG_PATH" >/dev/null

log "Writing checksums"
/usr/bin/shasum -a 256 "$ZIP_PATH" "$DMG_PATH" > "$CHECKSUM_PATH"
ls -lh "$APP_PATH" "$ZIP_PATH" "$DMG_PATH" "$CHECKSUM_PATH"
log "Release artifacts ready in $RELEASE_DIR"
