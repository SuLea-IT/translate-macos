#!/usr/bin/env python3
from pathlib import Path

workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "swift.yml"
project_file = Path(__file__).resolve().parents[1] / "LiveBuddy.xcodeproj" / "project.pbxproj"
text = workflow.read_text()
project_text = project_file.read_text()
errors: list[str] = []

if "swift build" in text or "swift test" in text:
    errors.append("workflow must not use swift build/test for this Xcode project")
if "xcodebuild build" not in text:
    errors.append("workflow must build with xcodebuild")
if "xcodebuild test" not in text:
    errors.append("workflow must test with xcodebuild")
if "LiveBuddy.xcodeproj" not in text:
    errors.append("workflow must reference LiveBuddy.xcodeproj")
if "-scheme LiveBuddy" not in text:
    errors.append("workflow must use the LiveBuddy scheme")
if "CODE_SIGNING_ALLOWED=NO" not in text:
    errors.append("workflow must disable code signing for CI")
if "-only-testing:LiveBuddyTests" not in text:
    errors.append("workflow must limit CI tests to the unit test target")
if "MACOSX_DEPLOYMENT_TARGET = 26.1;" in project_text:
    errors.append("project deployment targets must not require macOS 26.1 on CI")
if "MACOSX_DEPLOYMENT_TARGET = 14.6;" not in project_text:
    errors.append("project must keep macOS 14.6 as the supported deployment target")

if errors:
    print("CI workflow verification failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("CI workflow verification passed")
