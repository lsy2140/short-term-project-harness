# Modifications

This directory is a modified copy of Archify, provided under the Apache License 2.0 (Section 4(b)).

- Upstream: https://github.com/tt-a1i/archify, commit `d6059331abbddb49bca380ff46dca8ce33158b04`, directory `archify/` (v3.2.0)
- Date: 2026-10-29

## Changes

- `SKILL.md`: added a short usage note below the front matter and Korean trigger words at the end of `description`. The rest is unchanged.
- `locales/manifest.json`: reduced the catalog list to `en` and `ko`. Other locales fall back to English.
- Removed: rendered HTML examples, other locale catalogs, development generator scripts, and packaging scripts. Only the 21 example JSON files referenced by the code or `SKILL.md` were kept.
- Unchanged: `LICENSE`, `LICENSE-MIT`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, and the contents of all other files.
