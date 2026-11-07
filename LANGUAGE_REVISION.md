# English Software Revision

## Changes

- Translate the 12 reported source/test files, including Python comments, dialogs, terminal messages, plot labels and camera-source comments.
- Replace the 24 damaged calibration-guide comments with readable English descriptions.
- Default to English, normalize old saved language preferences to English, and remove the language-switch button.
- Use English-compatible plot fonts and retain all existing controls and numeric parameters.
- Add a regression check for non-ASCII text in distributed source, documentation, settings and tests.

## Preserved Behavior

CSV field names, condition naming, default trial duration, virtual geometry, coordinate integration, stimulus calculations and file formats are unchanged. The only changed default configuration value is `UI_LANGUAGE` (`en`).

The native FicTrac executables and required DLLs are unchanged from v1.1.1. FicTrac C++ changes are comments only; the automatic calibration-point behavior and recording implementation are preserved.

## Validation Scope

Core Python behavior was compared through syntax trees with presentation text excluded. Four deterministic trials produced byte-identical frame-level and summary CSV files against the previous logger. Program tests, GUI tests, mixed-DPI controls and historical 20-second replay are checked separately from physical hardware acceptance.

Plain-text payloads are checked as UTF-8 (an optional BOM is allowed) and must contain ASCII English text. Third-party EXE/DLL files are not rewritten to remove vendor language resources.

The 28 native CAD documents are retained unchanged. Their filenames are English, but their internal feature names, configurations, properties and annotations have not been certified as English-only. See `hardware/README.md` for the required manual check and the automation limitation.

## Repository Versions

This revision supersedes the software text in the teacher package based on commit e2274de. It does not replace the original thesis protocol or modify historical biological data. Previous packages remain versioned separately.

The revised ZIP includes a regenerated `MANIFEST.sha256`; its separate SHA256 file identifies the complete archive. To update an existing Figshare item, upload the revised ZIP as a new item version and retain the older version history. A GitHub release does not automatically update Figshare.
