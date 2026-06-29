# Terminology Glossary Design

## Goal

Let users protect names, product names, code terms, and preferred translations during live translation. The feature should be lightweight: persist small glossary entries, inject concise rules into Gemini setup, and avoid per-audio buffering or expensive runtime matching.

## References and Borrowed Ideas

- [OmegaT glossary files](https://omegat.sourceforge.io/manual-standard/en/chapter.appendices.html) use source term, target term, and optional comment columns. Borrow: simple user-editable terminology entries, not a database-heavy termbase.
- [Translate Toolkit's OmegaT glossary format](https://docs.translatehouse.org/projects/translate-toolkit/en/latest/formats/omegat_glossary.html) keeps glossary data as lightweight tabular terminology. Borrow: glossary is guidance, not transcript mutation.
- MT terminology-constrained decoding literature commonly treats longer phrase matches as more specific. Borrow: sort terms by normalized source length before generating prompt rules.

## Design

### Model

Add `Glossary.swift` with `GlossaryEntry`:

- stable `id: UUID`
- `sourceTerm`
- `targetTerm`
- `note`
- `isEnabled`

If `targetTerm` is empty, the rule means preserve the source term exactly.

Add `GlossaryPromptBuilder`:

- trims whitespace;
- skips disabled or empty source entries;
- de-duplicates by case-insensitive source term, keeping the first user entry;
- sorts by source term length descending;
- caps prompt rules to 80 entries to keep setup small;
- emits concise lines:
  - `- OpenAI => OpenAI`
  - `- Gemini Live => Gemini Live API`

Add `GlossaryEntryEditor`:

- normalizes whitespace on add;
- skips empty source terms;
- deletes by stable id;
- returns new arrays instead of mutating unrelated state.

### Settings and runtime

Add `AppSettings.glossaryEntries: [GlossaryEntry] = []` and include it in Codable. Changing entries requires a session restart because Gemini setup instructions change.

`GeminiLiveTranslateClient.setupInstruction()` prepends:

```text
Terminology rules:
- Keep source terms exactly when target is identical.
- Use these preferred terms when they appear in speech:
...
```

Then source-language hint, then user prompt.

### UI

In Settings → Translation & Audio, add a Glossary section:

- Source term field.
- Preferred translation field; empty means preserve original term.
- Add button.
- Compact list of current entries with delete buttons.

Menu bar is intentionally not used for glossary editing to keep it compact.

### Localization

Add eight-language keys:

- `terminologyGlossary`
- `sourceTerm`
- `preferredTranslation`
- `preserveOriginalTerm`
- `addTerm`
- `deleteTerm`

## Non-goals

- Import/export TBX/CSV in this pass.
- Per-segment glossary highlighting.
- Local NLP matching during audio streaming.
- Large terminology database.
