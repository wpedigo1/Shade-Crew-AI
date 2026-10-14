# Mission 039 — Fix Non-Deterministic Query Preprocessing

Route: Big Pickle (OpenCode Zen)
Punch Board items: none directly — pre-existing correctness bug, found via
Mission 038's own testing work.

Base: `main` @ `32c4e89` "fix(modelmix): correct RAKE keyword sort direction
(Mission 038 follow-up)".

Result: **PASS**. `_preprocess_query` now produces byte-identical output for
the same input across every tested `PYTHONHASHSEED` value (0–12 verified
individually), and the entire search test file passes under all 13 seeds. The
bug is pre-existing and pre-dates Mission 038; Mission 038 did not introduce
it (its sort-direction fix was correct — Mission 038's new tests were simply
the first ones with enough sensitivity to occasionally catch this much older,
separate bug).

## 1. Severity and provenance

Real, confirmed, pre-existing correctness bug. It predates ModelMix's own
`search.py` work entirely because it lives in `_preprocess_query` (`backend/
search.py`), which ran before the old YAKE call too.

Root cause, verified independently by running the same input across 13
different `PYTHONHASHSEED` values:

```text
PYTHONHASHSEED=5  -> 'current 2025 tesla stock'    (degraded)
PYTHONHASHSEED=11 -> 'current 2025 tesla stock'    (degraded)
PYTHONHASHSEED=12 -> 'current 2025 tesla stock'    (degraded)
seeds 0,1,2,3,4,6,7,8,9,10 -> 'tesla stock'        (correct)
```

Same code, same input, only the hash seed differs — roughly 3 of 13 (≈23%) of
process invocations produced a worse result. Never caught before because no
test exercised `_preprocess_query`'s actual behavior until Mission 038 added
the first coverage.

## 2. Root cause

`_preprocess_query` applies a SEQUENCE of interacting regex substitutions:

```python
for title in ROLE_PLAY_TITLES:
    cleaned = re.sub(rf'\b{re.escape(title)}\b', '', cleaned, flags=re.IGNORECASE)
for phrase in NOISE_PHRASES:
    cleaned = re.sub(rf'\b{re.escape(phrase)}\b', '', cleaned, flags=re.IGNORECASE)
```

`ROLE_PLAY_TITLES` and `NOISE_PHRASES` are plain, unordered Python `set`
literals. Python string-set iteration order depends on `PYTHONHASHSEED`
(default: a random, per-process value). Because the substitutions interact —
removing one phrase can alter surrounding text that a LATER phrase's
`\b...\b` word-boundary regex depends on matching — the final cleaned text was
not deterministic.

Directly confirmed mechanism for the flagged scenario
("Act as a financial analyst and evaluate the current market in late 2025 for
tesla stock"): when `current market` (a `NOISE_PHRASES` member) happens to be
matched and stripped first, the remainder loses `market`, so `late 2025` is
then also removed and the query cleans down to `tesla stock`. Under adverse
iteration orders (seeds 5/11/12), a different role-play/noise substitution ran
first and the `current market` regex then failed to match against the already-
altered string, leaving the degraded `current 2025` fragments behind.

`NOISE_WORDS` and `CURRENT_EVENT_INDICATORS` (also plain sets) were audited at
every use site and are used only for order-independent work: `in`/`not in`
membership checks, or summing a count via `if indicator in query_lower`. They
do not need the treatment and were left unchanged.

## 3. Fix (`backend/search.py`)

Two new module-level constants are iterated instead of the raw sets:

```python
_ROLE_PLAY_TITLES_DETERMINISTIC = tuple(
    sorted(ROLE_PLAY_TITLES, key=lambda s: (-len(s), s))
)
_NOISE_PHRASES_DETERMINISTIC = tuple(
    sorted(NOISE_PHRASES, key=lambda s: (-len(s), s))
)
```

* **Deterministic**: sorting is a pure function of the fixed set contents —
  the iteration order is identical on every process/Python version, so the
  sequential substitutions can no longer depend on hash randomization.
* **Longest-first + alphabetical tiebreak**: a stable, explicit, fully
  reproducible order (not merely "deterministic within one Python version").
  Longest-first also reduces the underlying interaction risk — removing a
  longer, more specific phrase first is less likely to fragment text a
  shorter phrase's regex still needs — rather than only making the existing
  interaction deterministically ordered.
* No change to `NOISE_WORDS` or `CURRENT_EVENT_INDICATORS`.
* No change to the regex patterns, to the CONTENTS of `ROLE_PLAY_TITLES` or
  `NOISE_PHRASES`, or to any other function. The deterministic order is a
  precomputed tuple, so `_preprocess_query`'s body differs only in which
  iterable the two `for` loops walk.

## 4. New test (`backend/tests/test_search_keywords.py`)

`test_preprocess_query_is_deterministic_across_hash_seeds` spawns **real
subprocesses** (`sys.executable -c ...`, `cwd` = repo root), one per seed in
`HASH_SEED_SWEEP = [0..12]`, each with its own `PYTHONHASHSEED` env override.
Each subprocess prints `repr((_preprocess_query(q), extract_search_keywords(q)))`
for the previously-flaky scenario; the test asserts all 13 snapshots are
identical AND that the extracted query is exactly `"tesla stock"`.

This methodology is required by the bug's nature: hash randomization is fixed
for the lifetime of one process, so a same-process parametrized test can never
observe it. The subprocess design matches exactly how the bug was originally
confirmed and is the test that would have caught it.

## 5. Validation (all actually run; raw pass/output for every seed)

13-seed sweep over the whole `test_search_keywords.py` file (required by the
mission — run separately under each `PYTHONHASHSEED`, not once):

```text
seed  0: 9 passed in 3.88s
seed  1: 9 passed in 3.88s
seed  2: 9 passed in 3.84s
seed  3: 9 passed in 3.88s
seed  4: 9 passed in 3.88s
seed  5: 9 passed in 3.88s
seed  6: 9 passed in 3.90s
seed  7: 9 passed in 3.88s
seed  8: 9 passed in 3.86s
seed  9: 9 passed in 3.90s
seed 10: 9 passed in 4.06s
seed 11: 9 passed in 4.01s
seed 12: 9 passed in 3.95s
```

(Before the fix, seeds 5/11/12 in this exact loop failed
`test_existing_noise_and_role_play_filtering_still_works_with_new_engine`
with produced `'current 2025 tesla stock'`.)

Post-fix direct seed probe of the exact scenario — `_preprocess_query` and
`extract_search_keywords` returned identical tuples for every seed 0–12:

```text
0..12: ('and evaluate the in for tesla stock', 'tesla stock')   # all 13
```

Full suite and frontend (unchanged by this mission, re-asserted):

```text
uv run pytest backend/tests -q --basetemp ... -> 477 passed in 39.35s
npm.cmd test   -> 138 passed (15 files)
npm.cmd run build -> built in 3.67s
npm.cmd run lint  -> eslint clean (exit 0)
uv run ruff check backend/search.py backend/tests/test_search_keywords.py -> All checks passed
```

(Plain `uv run pytest backend/tests -q` still needs the documented
`--basetemp` override in this environment for the pre-existing Windows
`pytest-of-wpedigo` temp-dir `WinError 5` issue.)

## 6. Files changed

* `backend/search.py` — deterministic ordered iterables added; the two
  preprocessing `for` loops walk them; `_preprocess_query` docstring documents
  the determinism guarantee. Set CONTENTS, regex patterns, and all other
  functions unchanged.
* `backend/tests/test_search_keywords.py` — new cross-seed subprocess
  determinism test (+1 test → 9 total).
* `docs/modelmix/039-fix-nondeterministic-query-preprocessing.md` (this report).
* Tracking docs: `MISSION-INDEX.md` (row 039 + result), `ENGINEERING-PROGRESS.md`
  (Mission 039 Result). No Punch Board item number is used — this is a
  pre-existing correctness bug found via Mission 038's own test coverage, not
  a board item.

## 7. Commit

`fix(modelmix): deterministic query preprocessing across process restarts (Mission 039)` — pushed, verified local == origin == live remote.

## 8. Notes

* Mission 038's sort-direction fix was correct and is untouched; this mission
  fixes a distinct, older bug that Mission 038's new test sensitivity merely
  surfaced. Not intended as a reflection on Mission 038.
* The deterministic order is a tuple built once at import; `_preprocess_query`
  cost is unchanged in practice (ordering remains constant folds for ~20-item
  sets).
* `NOISE_WORDS` / `CURRENT_EVENT_INDICATORS` were explicitly left as sets per
  the audit above — membership-only usage is order-independent and safe.