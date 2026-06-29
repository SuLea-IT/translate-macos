# Free Release Distribution Design

## Goal

Let the project publish a usable macOS release without paying for Apple Developer Program membership. The release should produce a clean `.app`, `.zip`, and `.dmg`, explain the macOS first-open security prompt, and provide an in-app way to check GitHub Releases manually.

## Constraints

- No Apple Developer ID certificate.
- No paid notarization.
- No Sparkle auto-update for this iteration because a smooth Sparkle path usually assumes signed update packages and an appcast.
- macOS Gatekeeper may show an “unidentified developer” warning. The product must explain the right-click Open flow clearly instead of pretending it is notarized.
- Local developer machines may only have Command Line Tools, while GitHub Actions macOS runners have full Xcode. The packaging script should prefer `xcodebuild` and fall back to `swiftc` for local ad-hoc builds when full Xcode is unavailable.

## User experience

1. User visits GitHub Releases.
2. User downloads either:
   - `LiveTranslateBuddy-macOS-arm64.dmg`, preferred for normal users.
   - `LiveTranslateBuddy-macOS-arm64.zip`, fallback archive.
3. DMG opens with:
   - `Live Translate Buddy.app`
   - `Applications` symlink
   - `INSTALL.txt` explaining first-open steps
4. If macOS blocks launch:
   - Right-click `Live Translate Buddy.app`
   - Choose Open
   - Confirm Open once
5. In the app, Settings shows a “Check for Updates” button that opens the GitHub Releases page.

## Packaging design

Add `scripts/package_release.sh`:

- Inputs:
  - `VERSION`, default from `git describe --tags --always`.
  - `RELEASE_DIR`, default `releases/` under repo root.
  - `APP_NAME`, default `Live Translate Buddy`.
  - `BUNDLE_ID`, default `com.sulea.translate-macos.LiveBuddy`.
- Build path:
  - Use `xcodebuild -project LiveBuddy.xcodeproj -scheme LiveBuddy -configuration Release` when full Xcode is active.
  - Fall back to `swiftc` source compilation for local free builds when only Command Line Tools are installed.
- Package path:
  - Create `Live Translate Buddy.app` with Info.plist and `AppIcon.icns`.
  - Sign ad-hoc with `codesign --sign -` and existing entitlements.
  - Generate a clean ZIP with `/usr/bin/zip -qry -X`, excluding `._*` and `__MACOSX`.
  - Generate a DMG staging folder with the app, `Applications` symlink, and `INSTALL.txt`.
  - Create compressed DMG using `hdiutil create -format UDZO`.
  - Verify app signature, ZIP content, DMG checksum, and SHA-256 checksums.

The script must fail fast with clear messages if required macOS tools are unavailable.

## GitHub Actions release workflow

Add `.github/workflows/release.yml`:

- Trigger:
  - `workflow_dispatch`
  - tag push matching `v*`
- Runner: `macos-latest`
- Steps:
  - Checkout
  - Select Xcode
  - Run `scripts/package_release.sh`
  - Upload artifacts for manual runs
  - On tag pushes, create a GitHub Release using `gh release create` and upload DMG/ZIP/checksum files.

No Apple secrets are required.

## In-app update check

Add a simple Settings button that opens:

`https://github.com/SuLea-IT/translate-macos/releases`

This is deliberately not background auto-update. It avoids unsigned auto-update complexity while still giving users a discoverable update path.

## Documentation

Update README with:

- Download from GitHub Releases.
- Prefer DMG.
- First-open right-click Open instructions.
- Explain this is a free ad-hoc signed build, not Apple-notarized.
- Explain users can use “Check for Updates” to open releases.

## Testing and verification

- Static script verifier confirms:
  - package script exists and is executable
  - release workflow triggers on tags and workflow dispatch
  - release workflow calls `scripts/package_release.sh`
  - README mentions right-click Open
- Local packaging verification confirms:
  - `.app` exists
  - `codesign --verify --deep --strict` succeeds
  - `.zip` contains no `._*` or `__MACOSX`
  - `.dmg` verifies with `hdiutil verify`
- Typecheck confirms app UI changes compile.
- GitHub Swift CI must pass after push.

## Out of scope

- Paid Developer ID signing.
- Apple notarization.
- Sparkle automatic background updates.
- Universal Intel+Apple Silicon build. This iteration publishes arm64 because current local and CI environments target Apple Silicon; universal packaging can be added later.
