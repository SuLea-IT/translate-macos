# Meeting Mode MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local transcript-based meeting notes with summary, key points, action items, timeline, copy, and Markdown export.

**Architecture:** Implement a pure `MeetingNotesGenerator` model with deterministic scoring and Markdown output, then integrate it into `TranscriptsView`. Keep transcript persistence unchanged and reuse `TranscriptExportDocument` for file export.

**Tech Stack:** Swift, SwiftUI, Foundation, existing Swift Testing tests, existing verifier scripts.

---

## Task 1: Meeting notes model and tests

**Files:**
- Create `LiveBuddy/Models/MeetingNotes.swift`
- Create `LiveBuddyTests/MeetingNotesTests.swift`

- [ ] Write failing tests for summary/key points, action cues, timeline, markdown, and empty transcripts.
- [ ] Implement model and generator.
- [ ] Run local focused executable checks and app source typecheck.
- [ ] Commit `feat: add meeting notes generator`.

## Task 2: Transcript UI integration

**Files:**
- Modify `LiveBuddy/Views/Settings/TranscriptsView.swift`
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`

- [ ] Add localized strings.
- [ ] Add Meeting Notes button and panel.
- [ ] Add copy and Markdown export actions.
- [ ] Run interface-language verifier and app source typecheck.
- [ ] Commit `feat: add meeting notes UI`.

## Task 3: Documentation and final verification

**Files:**
- Modify `README.md`

- [ ] Document meeting notes feature.
- [ ] Run all verifiers and typecheck.
- [ ] Push to target main and wait for CI.
