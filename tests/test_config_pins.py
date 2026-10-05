"""The tuned constants in src/pipeline/config.py are held to the places that
state them (Stage 48 item 15, proposed 2026-10-04).

Until this file, no test failed when a tuned constant changed. Checked on
2026-10-05 at 86563df: with QB_SHRINK_K 8 -> 96, RIDGE_ALPHA 15.0 -> 5.0 and
RECENCY_HALF_LIFE 16 -> 10 all at once, the full suite still passed, because
every test reads them symbolically. That is right for a test of the
engine and wrong for the project: each constant was chosen by a backtest,
CLAUDE.md states it as the current model, and the published figures were
computed with it. Changing one is a model change -- re-run the backtest,
regenerate the published figures, bump MODEL_VERSION -- and the edit to the
statement below is the moment someone has to say so.

What these hold is agreement between the code and the two places that
describe it, not a value: change the constant AND the statement together.
"""
import json
import re
from pathlib import Path

from src.pipeline import config

ROOT = Path(__file__).resolve().parents[1]
STATE = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8').split('## Current state', 1)[1][:2000]


def _span(name):
    m = re.search(rf'`{name}` (\d{{4}})-(\d{{4}})', STATE)
    assert m, f"CLAUDE.md's Current state no longer states {name} as a range"
    return list(range(int(m.group(1)), int(m.group(2)) + 1))


def _value(name):
    m = re.search(rf'`{name} = ([\d.]+)`', STATE)
    assert m, f"CLAUDE.md's Current state no longer states {name}"
    return float(m.group(1))


def test_the_model_version_is_the_one_claude_md_describes():
    m = re.search(r'Model v(\d+\.\d+) \(`MODEL_VERSION`', STATE)
    assert m and m.group(1) == config.MODEL_VERSION, (
        f'CLAUDE.md describes v{m and m.group(1)}; config says {config.MODEL_VERSION}')


def test_the_tuned_constants_are_the_ones_claude_md_states():
    for name in ('QB_SHRINK_K', 'RIDGE_ALPHA', 'RECENCY_HALF_LIFE'):
        assert getattr(config, name) == _value(name), (
            f'config.{name} is {getattr(config, name)} but CLAUDE.md states {_value(name)}. '
            f'A tuned constant changing is a model change: re-run the backtest, regenerate '
            f'the published figures, bump MODEL_VERSION, then update the statement.')


def test_the_seasons_are_the_ones_claude_md_states():
    assert config.TRAIN_SEASONS == _span('TRAIN_SEASONS')
    assert config.BACKTEST_SEASONS == _span('BACKTEST_SEASONS')


def test_the_published_backtest_used_these_seasons():
    """data/calibration.json is the published backtest's artifact; the
    drift baseline is read from it. Its seasons must be config's."""
    published = json.loads((ROOT / 'data' / 'calibration.json').read_text(encoding='utf-8'))
    assert published['backtest_seasons'] == config.BACKTEST_SEASONS


def test_the_backtest_seasons_are_validation_then_confirmation():
    """CLAUDE.md's methodology: tune on [2022, 2023], confirm on [2024, 2025]."""
    method = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    m = re.search(r'\*\*validation\*\* seasons \[(\d{4}), (\d{4})\]; confirm on held-out \[(\d{4}), (\d{4})\]',
                  method)
    assert m, 'CLAUDE.md no longer states the validation and confirmation seasons'
    assert config.BACKTEST_SEASONS == [int(g) for g in m.groups()]
