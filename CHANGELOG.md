# Changelog

All notable changes to CmdVault are documented here.

## [2.0.0] - 2026-02-27

### Added

- **Developer Tool theme:** Slate/Zinc dark theme by default; Inter + JetBrains Mono typography.
- **Notes tab:** Two-column grid; add/edit/delete notes. **Copy** (content only) and **Copy with title** (right-click).
- **Todo tab:** Daily tasks with segment filter (All | Pending | Done), double-click to complete, Clear completed.
- **Command tags:** Colored tags (e.g. Production, Debug) on commands; editable in Add/Edit dialog.
- **Global search:** Search bar in header (all tabs); recent searches dropdown; fast in-memory filter with result cap.
- **Toasts:** “Copied to clipboard” toast instead of status bar for copy actions.
- **Secrets:** “Show” to reveal value without editing.
- **Bulk actions:** Checkboxes on command cards; Bulk Delete and Bulk Export to JSON.
- **Ghost actions:** Copy/Edit/Delete on command cards shown on hover.
- **Sample data:** `samples/import_sample.json` with DevStack and OpenStack commands.

### Changed

- Default theme is dark (Developer Tool aesthetic).
- Search is faster (no difflib; cached results; display limit).
- Project layout: `docs/`, `samples/`, `tests/` for a clearer structure.

## [1.0.0] - 2026-02-28

### Added

- Initial release: Commands, Secrets, categories, fuzzy search, dark mode toggle, import from JSON.
