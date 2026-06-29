#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

for token in [
    "private static let maxTranscriptDraftCharacters",
    "private static let maxPendingOriginalSentences",
    "private static let maxPendingOriginalSentenceCharacters",
]:
    if token not in text:
        errors.append(f"AppState must bound live transcript draft memory through {token}")

for helper in [
    "private func boundedTranscriptDraft(_ text: String) -> String",
    "private func boundedOriginalSentence(_ sentence: String) -> String",
    "private func trimPendingOriginalSentences()",
]:
    if helper not in text:
        errors.append(f"AppState must provide bounded live transcript helper {helper}")

append_original_match = re.search(r"private func appendOriginalText\(_ text: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func appendCaption", text)
if not append_original_match:
    errors.append("AppState.appendOriginalText(_:) not found")
else:
    body = append_original_match.group("body")
    for token in [
        "let pending = boundedTranscriptDraft(originalDraft + (originalDraft.isEmpty ? \"\" : \" \") + trimmed)",
        "completedOriginalSentences.append(boundedOriginalSentence(sentence))",
        "trimPendingOriginalSentences()",
        "originalDraft = boundedTranscriptDraft(sentences.remainder)",
    ]:
        if token not in body:
            errors.append(f"appendOriginalText must bound original draft and pending sentence queue through {token}")

append_caption_match = re.search(r"private func appendCaption\(_ text: String, language: String\?, kind: CaptionKind\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func appendCurrentTranscriptLine", text)
if not append_caption_match:
    errors.append("AppState.appendCaption(_:language:kind:) not found")
else:
    body = append_caption_match.group("body")
    for token in [
        "var pending = boundedTranscriptDraft(captionDraft + (captionDraft.isEmpty ? \"\" : \" \") + trimmed)",
        "captionDraft = boundedTranscriptDraft(pending)",
    ]:
        if token not in body:
            errors.append(f"appendCaption must bound translated draft memory through {token}")

helper_match = re.search(r"private func trimPendingOriginalSentences\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func appendCaption", text)
if not helper_match:
    errors.append("AppState.trimPendingOriginalSentences() helper not found before appendCaption")
else:
    body = helper_match.group("body")
    for token in [
        "completedOriginalSentences.count > Self.maxPendingOriginalSentences",
        "completedOriginalSentences.removeFirst",
    ]:
        if token not in body:
            errors.append(f"trimPendingOriginalSentences must drop oldest unmatched original sentences through {token}")

if errors:
    print("Transcript draft bounds verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript draft bounds verification passed")
