"""Tests for keyword extraction in backend.search (Mission 038).

Mission 038 replaced the YAKE library with a stdlib-only RAKE implementation,
which is covered by tests here for the first time. The assertions rely on the
deterministic output of the current implementation together with the unchanged
NOISE_WORDS / NOISE_PHRASES / ROLE_PLAY_TITLES filtering that lives downstream
of the extraction call.

RAKE's real sort convention applies: a higher degree/frequency word score means
a word is more central, so the extraction returns the highest-scored (most
important) phrases first. The semantic tests below assert the subject phrase
must appear contiguously in the output - shape-only tests ("is non-empty")
cannot catch an inverted sort, which is exactly the regression these guard.

Mission 039 (this file's cross-seed test) additionally locks down
preprocessing determinism: the interactive role-play/noise regex passes used
to depend on PYTHONHASHSEED via plain-set iteration order, flaking ~1 in 5
processes. That bug predates Mission 038 and was only catchable from a
subprocess, because hash randomization is fixed for the lifetime of one
process.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

from backend.search import (
    _rake_extract_keywords,
    extract_search_keywords,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Seeds sweep matching how the nondeterminism was confirmed: real subprocesses,
# each with its own hash seed. The original bug made ~3 of every 13 seeds
# produce a degraded result for the query below.
HASH_SEED_SWEEP = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

_PREPROCESS_DETERMINISM_QUERY = (
    "Act as a financial analyst and evaluate the current market in late "
    "2025 for tesla stock"
)


def test_short_query_returned_unchanged():
    assert extract_search_keywords("hi there") == "hi there"
    assert extract_search_keywords("Tesla") == "Tesla"
    assert extract_search_keywords("") == ""
    assert extract_search_keywords("   ") == ""


def test_normal_query_returns_nonempty_keywords():
    result = extract_search_keywords(
        "What is the impact of artificial intelligence on the healthcare industry in 2026"
    )
    assert isinstance(result, str)
    assert result
    assert "artificial" in result
    assert "intelligence" in result


def test_max_keywords_is_respected():
    query = (
        "What is the impact of artificial intelligence on the healthcare "
        "industry in 2026"
    )
    top = extract_search_keywords(query, max_keywords=1)
    full = extract_search_keywords(query, max_keywords=6)
    assert top == "artificial intelligence"
    assert full == "artificial intelligence healthcare industry"
    assert len(top.split()) <= len(full.split())
    assert top in full


def test_candidates_are_limited_to_three_words_and_sorted_descending():
    keywords = _rake_extract_keywords(
        "artificial intelligence healthcare industry standardization committee"
    )
    assert keywords
    for phrase, score in keywords:
        assert isinstance(score, float)
        assert len(phrase.split()) <= 3
    # RAKE convention: HIGHER degree/frequency score = more central/important,
    # so the list is ordered highest-score-first, which is exactly the
    # direction the caller's existing filtering loop iterates in.
    scores = [score for _, score in keywords]
    assert scores == sorted(scores, reverse=True)


def test_existing_noise_and_role_play_filtering_still_works_with_new_engine():
    result = extract_search_keywords(
        "Act as a financial analyst and evaluate the current market in late "
        "2025 for tesla stock"
    )
    # Role-play titles and noise phrases are still stripped.
    assert "financial analyst" not in result
    assert "market in late" not in result
    assert "analyst" not in result
    # The multi-word subject phrase is the top-ranked phrase and survives:
    # 'evaluate' (a single-word noise token) is dropped while the subject
    # phrase 'tesla stock' carries the query intent.
    assert result == "tesla stock"


def test_noise_phrase_words_do_not_survive_extraction():
    result = extract_search_keywords(
        "Provide a market analysis for electric vehicles in late 2025"
    )
    assert "late 2025" not in result
    assert "in 2025" not in result
    assert "electric" in result
    assert "vehicles" in result


def test_subject_phrase_survives_extraction_unaltered():
    # Semantic check, not just shape: a clear multi-word subject phrase must
    # appear contiguously in the returned keywords. This assertion fails under
    # an inverted RAKE sort, where the low-scored noise leads (e.g.
    # 'economic arguments income universal basic' for this query).
    result = extract_search_keywords(
        "Discuss the economic arguments for universal basic income"
    )
    assert "universal basic income" in result


def test_climate_change_policy_phrase_survives_extraction():
    # Same semantic guarantee for a different subject phrase: the contiguous
    # multi-word subject must survive, not merely some of its words.
    result = extract_search_keywords(
        "Compare the main climate change policy proposals for 2026"
    )
    assert "climate change policy" in result


def _run_preprocess_snapshot(seed):
    """Run preprocessing + extraction in a fresh subprocess under a hash seed.

    Returns (preprocessed, extracted) for that seed's process, or raises if
    the subprocess fails. A same-process test cannot observe hash-seed
    variance, so the sweep must spawn real subprocesses.
    """
    code = (
        "from backend.search import _preprocess_query, extract_search_keywords;"
        "q = %r;"
        "print(repr((_preprocess_query(q), extract_search_keywords(q))))"
        % _PREPROCESS_DETERMINISM_QUERY
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "PYTHONHASHSEED": str(seed)},
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return ast.literal_eval(result.stdout.strip())


def test_preprocess_query_is_deterministic_across_hash_seeds():
    """Same input, 13 different PYTHONHASHSEED processes -> identical output.

    This is the regression test for the pre-existing bug where the sequential
    ROLE_PLAY_TITLES / NOISE_PHRASES regex substitutions iterated plain sets,
    so the iteration order (and thus the interaction between substitutions)
    depended on the process's hash seed. It produces 'tesla stock' for every
    seed in the sweep, never the degraded 'current 2025 tesla stock'.
    """
    snapshots = {seed: _run_preprocess_snapshot(seed) for seed in HASH_SEED_SWEEP}

    preprocessed = {seed: snap[0] for seed, snap in snapshots.items()}
    extracted = {seed: snap[1] for seed, snap in snapshots.items()}

    assert len(set(preprocessed.values())) == 1, preprocessed
    assert len(set(extracted.values())) == 1, extracted
    assert extracted[HASH_SEED_SWEEP[0]] == "tesla stock"