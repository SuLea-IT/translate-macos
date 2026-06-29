# Glossary Imports and Public Terminology Sources Design

## Goal

Improve the current manual-only terminology glossary so users can quickly build a useful local glossary by downloading public terminology resources, importing a user-provided link, or importing a local file. The feature must remain lightweight for a real-time translation app: downloads are cached on disk, parsing is bounded, and only selected/imported terms are added to `AppSettings.glossaryEntries` for prompt injection.

## Reference behavior from open terminology tools and sources

- Microsoft Terminology provides public software/localization terminology downloads in TBX-style packages. We will borrow the idea of a downloadable, curated IT/software source, but not bundle large files in the app.
- IATE provides large public multilingual terminology exports and download workflows. We will support user-provided IATE CSV/TBX exports or links, but will not hard-code login-only generated URLs.
- OmegaT and Translate Toolkit document the simple glossary pattern of source term, target term, and optional comment columns. We will support this lightweight TSV shape as the easiest user-editable import format.
- TBX is common for terminology interchange. We will implement a conservative TBX parser that extracts term pairs for the selected source and target language without loading the whole file as app state.

## User experience

In Settings → Translation & Audio → Terminology Glossary, add an import area below the existing manual add row:

1. Public terminology sources:
   - A source picker with at least “Microsoft Terminology” and “Custom link”.
   - For IATE, show it as “IATE export / custom link” with helper text because the user may need to export or paste a generated CSV/TBX link.
   - A “Download / Import” action that downloads to local cache, parses, and imports terms.

2. Custom link import:
   - A text field for `https://...` URLs.
   - Accepted extensions: `.csv`, `.tsv`, `.txt`, `.tbx`, `.xml`, `.zip`.
   - Non-HTTPS links are rejected unless the URL is `file://` from local import flow.

3. Local file import:
   - A file picker for CSV, TSV, TXT, TBX/XML, and ZIP.
   - Same parser path as downloaded files.

4. Import controls and feedback:
   - Import limit defaults to 500 terms and is capped at 2,000 terms.
   - Import result displays: added, skipped empty, skipped duplicate, skipped unsupported, and source name.
   - Imported entries include `note` metadata such as `Imported from Microsoft Terminology` or `Imported from custom link`.

## Data model

Keep existing `GlossaryEntry` unchanged for compatibility:

```swift
struct GlossaryEntry: Identifiable, Codable, Equatable, Hashable {
    var id: UUID
    var sourceTerm: String
    var targetTerm: String
    var note: String
    var isEnabled: Bool
}
```

Add pure helper models in `GlossaryImport.swift`:

```swift
struct GlossaryImportSource: Identifiable, Equatable {
    enum Kind: Equatable { case builtIn(URL), customURL, localFile }
    var id: String
    var displayName: String
    var detail: String
    var kind: Kind
}

struct GlossaryImportOptions: Equatable {
    var sourceLanguageCode: String
    var targetLanguageCode: String
    var importLimit: Int
}

struct GlossaryImportResult: Equatable {
    var sourceName: String
    var added: Int
    var skippedEmpty: Int
    var skippedDuplicate: Int
    var skippedUnsupported: Int
    var totalParsed: Int
    var entries: [GlossaryEntry]
}
```

The import helper returns entries separately. `AppState` is responsible for merging them into settings.

## Parsing and merge algorithm

`GlossaryImportParser` chooses parser by file extension and lightweight content sniffing:

1. ZIP:
   - Inspect archive entries.
   - Parse only supported files.
   - Skip hidden files, directories, files over a per-file size limit, and unsupported extensions.
   - Stop once the import limit is reached.

2. TSV / TXT:
   - Read line by line.
   - Split by tab.
   - Accept first two columns as source and target.
   - Third column becomes note suffix if present.

3. CSV:
   - Use a small RFC-4180-style row parser for quoted fields.
   - If headers contain `source`, `sourceTerm`, `term`, `target`, `targetTerm`, or `translation`, map by header.
   - Otherwise use the first two columns.

4. TBX / XML:
   - Use `XMLParser` streaming callbacks.
   - Track `langSet xml:lang` / `langSet lang` language values.
   - Collect `term` text values by language.
   - Pair selected source-language terms with selected target-language terms within the same concept entry.
   - If language codes are missing, fall back to first two language buckets.

5. Merge:
   - Normalize whitespace using the same rules as `GlossaryEntryEditor`.
   - Skip entries with empty source terms.
   - De-duplicate case-insensitively against existing settings entries and terms parsed earlier in the same import.
   - Keep first occurrence to preserve curated source order.
   - Cap imported entries by `importLimit` after de-duplication.

## Download and caching

Add `GlossaryImportService`:

- Uses `URLSession` for HTTPS downloads.
- Saves the raw file under `Application Support/LiveBuddy/GlossaryImports/`.
- File names include a sanitized source id and a short stable hash of the URL.
- Enforces a download size cap before parsing. Default cap: 25 MB.
- Returns clear user-facing status for unsupported URL, download failure, oversized file, unsupported format, empty result, and successful import.

Downloads are not parsed directly from memory. The service downloads to a temporary file, moves it into cache, then parses from disk.

## UI integration

Add state to `SettingsView` for import URL, selected source, import limit, and last result text. Keep UI minimal and consistent with the existing glossary section.

Add `AppState` methods:

```swift
func importGlossary(from url: URL, sourceName: String, importLimit: Int) async
func importGlossary(fromLocalFile url: URL, sourceName: String, importLimit: Int) async
```

Both methods use `GlossaryImportService`, merge returned entries into `settings.glossaryEntries`, save settings through the existing path, refresh setup checklist, and report localized status.

## Localization

Add interface strings for:

- Public terminology sources
- Import from link
- Import from file
- Download and import
- Import limit
- Import result
- Added terms
- Skipped duplicates
- Unsupported glossary format
- Glossary download failed
- Glossary import empty
- HTTPS links only

At minimum, provide translations for the existing app languages using concise UI labels. If a translation is uncertain, use clear English fallback text rather than leaving a key blank.

## Error handling and security

- Reject non-HTTPS remote URLs.
- Do not execute any downloaded content.
- Do not allow path traversal from ZIP entries.
- Skip hidden macOS metadata files such as `__MACOSX` and `._*`.
- Limit download size, per-file parse size, parsed row count, and imported result count.
- Treat malformed rows as skipped unsupported, not fatal, unless no rows can be parsed.

## Testing

Add unit tests for:

1. TSV import trims whitespace and uses the optional comment column.
2. CSV import handles quoted commas and header mapping.
3. Duplicate source terms are skipped case-insensitively against existing settings terms.
4. Import limit is enforced after de-duplication.
5. TBX parser extracts source/target terms from `langSet` blocks.
6. ZIP parser skips hidden files and unsupported files.
7. URL validator rejects `http://` and accepts `https://`.
8. `AppState` merge path appends imported entries and preserves existing entries.

## Out of scope for this iteration

- Full terminology database search UI.
- Background scheduled updates.
- Automatic language-pair discovery UI beyond best-effort TBX parsing.
- Editing imported source packages in place.
- Shipping large public terminology datasets inside the app bundle.
