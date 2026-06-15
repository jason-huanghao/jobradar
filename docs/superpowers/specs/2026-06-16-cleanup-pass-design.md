# Cleanup Pass — Design Spec (sub-project #5)

**Status:** approved (PM-authored, autonomous)
**Date:** 2026-06-16
**Branch:** `refactor/cleanup-pass`
**Depends on:** #1–#4 — all merged.

## Problem

Accumulated debt deferred through #1–#4:

- **73 ruff errors** in `src/` (E741, F401, F541, F841, I001, N806, E402, E401, E501).
  CI *runs* ruff but with `ruff check … --ignore E501 || true` — the `|| true` makes it
  **non-blocking**, so debt never fails a build and keeps growing.
- **Three** hardcoded provider tables: `cli._PROVIDERS` (now derived from the catalog in
  #4), `env_probe._PROBE_TABLE`, and `skill._PROVIDER_MAP`. The "CLI/skill dedup" item =
  fold `skill._PROVIDER_MAP` onto the catalog.
- `LLMClient.complete_auto` hardcodes a provider **blocklist**
  `("volcengine", "ollama", "lm_studio")` for json-mode — now expressible via the
  catalog's `supports_json_mode`.
- A stray unused `AppConfig` import in `arbeitsagentur.py`; one E402 from #4's catalog
  import in `cli.py`.

## Scope (PM)

1. **complete_auto → catalog-driven.** Replace the hardcoded blocklist with
   `get_provider(provider).supports_json_mode`.
2. **CLI/skill dedup.** `skill._PROVIDER_MAP` derives from `llm.catalog.CATALOG`.
3. **Zero the ruff debt** in `src/` and `tests/`, then make CI lint **blocking**.
4. Fix the `arbeitsagentur` F401 and the `cli.py` E402.

### Ruff policy decision
`E501` (line length) is **globally ignored** (added to `[tool.ruff.lint].ignore`).
Rationale: the bulk of E501 is long HTML-template strings (`report/generator.py`), long
help text, and prompt strings — rewrapping them is churn with regression risk and no
readability gain. This matches CI's existing `--ignore E501` intent. Every *other*
category is fixed and enforced. CI becomes:
`ruff check src/ tests/` (blocking, config from pyproject: select E,F,I,N,W; ignore E501).

### Not in scope
- `env_probe._PROBE_TABLE`: its concern is env-var *scan order/priority* for
  auto-detect, structurally different from the presentation catalog. Left as-is with a
  pointer comment. (Folding it in is a larger refactor with auto-detect-behavior risk.)
- `_MAX_DESC_CHARS` (the "400-char truncation" item): already a named constant in
  `scorer.py`, consistent with the prompt template's `[:400]`. No change needed.
- Behavioral changes of any kind — this is lint + dedup only.

## Success criteria

1. `ruff check src/ tests/` exits 0.
2. `tests/test_cleanup.py` covers: `complete_auto` selects structured parsing for a
   non-json-mode provider (e.g. volcengine/ollama) and json mode otherwise, driven by the
   catalog; `skill._PROVIDER_MAP` matches the catalog's `api_key_env → (base_url, model)`.
3. All pre-existing tests still pass (80 → 80+new). No behavioral diffs.
4. CI lint step is blocking (no `|| true`).
