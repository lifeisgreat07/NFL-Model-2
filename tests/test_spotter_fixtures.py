"""Spotter's regression fixtures (Stage 43 item 4; decision record 0007).

A planted defect Spotter must name and a clean change it must leave alone,
each a small stylesheet change opened as a draft pull request and read once.
Asking costs a model run; these tests re-check the answer for free.
"""
import copy
import json
import shutil
from pathlib import Path

import pytest

from src.agents import spotter_fixtures as sf
from src.agents import spotter_pages

FIXTURES = sf.load_all()
IDS = [m['id'] for m in FIXTURES]
DEFECTS = next(m for m in FIXTURES if m['id'] == 'planted-defects')
CLEAN = next(m for m in FIXTURES if m['id'] == 'clean-control')

NAMES = ['nhl-390x844-dark-head', 'nhl-390x844-light-head', 'nhl-1440x900-dark-head']


def reading(wrong: str) -> str:
    return ('#### What changed\n\nOnly `nhl-390x844-dark-head` differs.\n\n'
            f'#### What looks wrong\n\n{wrong}\n\n'
            '#### What looks fine\n\nThe header.\n\n#### What I could not tell\n\nNothing.\n')


BOTH = reading(
    '- `nhl-390x844-dark-head` and `nhl-390x844-light-head`: the page is far wider than the phone screen.\n'
    '- `nhl-390x844-dark-head` and `nhl-1440x900-dark-head`: the "Live" label is dim and hard to read.')


def test_the_two_fixtures_are_the_two_the_stage_names():
    assert IDS == ['clean-control', 'planted-defects']


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_a_fixture_is_complete_and_its_folder_is_its_id(meta):
    assert not [k for k in sf.REQUIRED if k not in meta]
    assert Path(meta['_path']).name == meta['id']
    assert (Path(meta['_path']) / meta['change']).is_file()
    assert meta['expect']['kind'] in ('defects', 'clean')
    if meta['expect']['kind'] == 'defects':
        for d in meta['expect']['defects']:
            assert d['pictures_any'] and d['words_any'], d['id']
            assert all(p.startswith(meta['page'] + '-') and p.endswith('-head') for p in d['pictures_any'])


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_a_fixture_names_a_page_spotter_renders_for_its_target(meta):
    hit = spotter_pages.rule_for(meta['target'])
    assert hit is not None and meta['page'] in hit[1]
    assert (sf.REPO / meta['target']).is_file()


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_every_class_a_change_names_is_drawn_by_the_page_that_is_photographed(meta):
    # The first trial planted .nhl-table, which the day board never draws.
    assert sf.unrendered_classes(meta) == []


def test_a_class_the_day_board_does_not_draw_is_refused():
    wrong = copy.deepcopy(DEFECTS)
    script = (sf.REPO / DEFECTS['script']).read_text(encoding='utf-8')
    assert sf.unrendered_classes(wrong, script.replace('nhl-row-result', 'nhl-row-outcome')) == ['nhl-row-result']
    assert sf.unrendered_classes(wrong, script.replace('function rowHtml(', 'function rowHtmlGone(')) == [
        'function rowHtml() is not in src/sports/nhl/pages/nhl.js']
    # a longer class that starts with the name is not the name
    assert sf.unrendered_classes(wrong, script.replace('<ul class="nhl-rows">', '<ul class="nhl-rows-x">')) == ['nhl-rows']
    # .nhl-table is drawn by the standings page, not by the board's functions
    standings = {**wrong, 'rendered_by': ['renderStandings']}
    assert set(sf.unrendered_classes(standings, script)) == {'nhl-rows', 'nhl-row-result'}


def test_the_clean_change_adds_no_declaration_the_file_does_not_already_make():
    css = (sf.REPO / CLEAN['target']).read_text(encoding='utf-8')
    assert sf.adds_nothing_new(CLEAN, css) == []
    # the same text against a file that lacks the declaration is a real change
    assert sf.adds_nothing_new(CLEAN, css.replace('font-weight:700;', '')) != []


def test_the_planted_change_adds_declarations_the_file_did_not_have():
    css = (sf.REPO / DEFECTS['target']).read_text(encoding='utf-8')
    new = sf.adds_nothing_new(DEFECTS, css)
    assert len(new) == 2 and any('min-width' in n for n in new) and any('#26262a' in n for n in new)


def test_a_reading_that_names_both_defects_satisfies_the_planted_fixture():
    ok, why = sf.satisfied_by(DEFECTS, BOTH)
    assert ok, why


@pytest.mark.parametrize('wrong, missing', [
    ('- `nhl-390x844-dark-head`: the page is far wider than the phone screen.', 'dark-result-unreadable'),
    ('- `nhl-1440x900-dark-head`: the "Live" label is dim and hard to read.', 'phone-overflow'),
    ('Nothing that I can see.', 'the page has planted defects'),
    ('- `nhl-1440x900-light-head`: the page is far wider than the phone screen, and a label is dim.',
     'phone-overflow, dark-result-unreadable'),
    ('- The page is far wider than the phone screen, and a label is dim and hard to read.',
     'phone-overflow, dark-result-unreadable'),
    ('- `nhl-390x844-dark-head` looks a little different from the base.', 'phone-overflow, dark-result-unreadable'),
], ids=['one-defect-only', 'other-defect-only', 'nothing', 'wrong-picture', 'no-picture', 'no-word'])
def test_a_reading_that_misses_a_planted_defect_does_not_satisfy_it(wrong, missing):
    ok, why = sf.satisfied_by(DEFECTS, reading(wrong))
    assert not ok
    if missing:
        assert why.endswith(missing)


def test_both_defects_in_one_bullet_count_when_it_cites_a_picture_for_each():
    one = reading('- `nhl-390x844-dark-head`: the rows are wider than the screen and the labels are dim.')
    assert sf.satisfied_by(DEFECTS, one)[0]


def test_a_reading_with_no_wrong_section_satisfies_nothing():
    assert sf.satisfied_by(DEFECTS, '#### What changed\n\nx\n')[0] is False
    assert sf.satisfied_by(CLEAN, '#### What changed\n\nx\n')[0] is False


STANDING = ('- `nhl-390x844-dark-head`: the tab bar sits mid-page. The same appears in `nhl-390x844-dark-base`.\n'
            '- `nhl-1440x900-dark-head`: the sidebar ends at 900px; the base pictures show it too.\n\n'
            'I see no overflow at 390 wide.')


def test_the_clean_fixture_wants_nothing_blamed_on_the_change():
    assert sf.satisfied_by(CLEAN, reading('Nothing that I can see.'))[0]
    noted = reading('Nothing that I can see.\n\nOn the phone pictures the tab bar sits mid-page in both.')
    assert sf.satisfied_by(CLEAN, noted)[0]
    # the protocol asks for standing quirks to be listed; saying the base has them is fine
    assert sf.satisfied_by(CLEAN, reading(STANDING)) == (
        True, 'every problem the reading lists is one the base picture shows too')
    # a problem the base does not have is blamed on the change
    assert not sf.satisfied_by(CLEAN, reading('- `nhl-390x844-dark-head`: the page is far wider than the phone screen.'))[0]
    assert not sf.satisfied_by(CLEAN, reading(STANDING + '\n- `nhl-390x844-dark-head`: the labels are dim.'))[0]
    assert not sf.satisfied_by(CLEAN, reading('Nothing that I can see.\n- `nhl-390x844-dark-head`: wider.'))[0]
    assert not sf.satisfied_by(CLEAN, reading('The page is far wider than the phone screen.'))[0]


def comment(body: str, head: str = 'f4e5fd8a1b2c') -> str:
    pics = ' / '.join(f'[x](https://github.com/o/r/blob/spotter-renders/pr-1/{head}/{n}.png?raw=true)' for n in NAMES)
    return (f'{sf.spotter_comment.MARKER}\n## Spotter\n\nHead `{head}` against its base.\n\n{pics}\n\n'
            f'### Reading\n\n{body}')


def test_a_spotter_comment_parses_to_its_reading_its_pictures_and_its_head():
    text, names, head = sf.parse_comment(comment(BOTH))
    assert text.startswith('#### What changed')
    assert names == sorted(NAMES) and head == 'f4e5fd8a1b2c'
    with pytest.raises(ValueError):
        sf.parse_comment('## Booth Audit: PR #1\n### Reading\n')
    with pytest.raises(ValueError):
        sf.parse_comment(sf.spotter_comment.MARKER + '\nno reading here')


def scratch(tmp_path: Path, meta: dict) -> dict:
    """A copy of a fixture's folder that can be written to."""
    dest = tmp_path / meta['id']
    shutil.copytree(meta['_path'], dest, ignore=shutil.ignore_patterns('baseline.json'))
    out = copy.deepcopy(meta)
    out['_path'] = str(dest)
    return out


def test_record_writes_a_baseline_that_check_passes(tmp_path):
    meta = scratch(tmp_path, DEFECTS)
    ok, _ = sf.record(meta, comment(f'{BOTH}'), 532, 'f4e5fd8a1b2c9999')
    assert ok
    assert sf.check_one(meta) == (True, 'the reading named every planted defect: phone-overflow, dark-result-unreadable')
    saved = json.loads(sf.baseline_path(meta).read_text(encoding='utf-8'))
    assert saved['pr'] == 532 and saved['change_sha256'] == sf.change_sha(meta)


def test_record_refuses_a_reading_of_another_commit(tmp_path):
    meta = scratch(tmp_path, DEFECTS)
    ok, why = sf.record(meta, comment(BOTH), 532, '0123456789ab')
    assert not ok and 'names head' in why
    assert sf.load_baseline(meta)['satisfied'] is False


def test_a_missed_defect_is_recorded_and_fails_the_check(tmp_path):
    meta = scratch(tmp_path, DEFECTS)
    ok, _ = sf.record(meta, comment(reading('Nothing that I can see.')), 531, 'f4e5fd8a1b2c')
    assert not ok
    assert sf.check_one(meta)[0] is False


def test_a_baseline_stops_counting_when_the_change_is_edited(tmp_path):
    meta = scratch(tmp_path, DEFECTS)
    sf.record(meta, comment(BOTH), 532, 'f4e5fd8a1b2c')
    assert sf.check_one(meta)[0] is True
    p = Path(meta['_path']) / meta['change']
    p.write_text(p.read_text(encoding='utf-8') + '\n/* edited */\n', encoding='utf-8')
    ok, why = sf.check_one(meta)
    assert ok is False and 'edited' in why


def test_a_baseline_stops_counting_when_the_answer_key_changes(tmp_path):
    meta = scratch(tmp_path, DEFECTS)
    sf.record(meta, comment(BOTH), 532, 'f4e5fd8a1b2c')
    meta['expect']['defects'][0]['words_any'] = ['kaleidoscope']
    assert sf.check_one(meta)[0] is False


def test_a_stored_reading_that_would_be_refused_today_stops_counting(tmp_path):
    meta = scratch(tmp_path, DEFECTS)
    sf.record(meta, comment(BOTH), 532, 'f4e5fd8a1b2c')
    saved = json.loads(sf.baseline_path(meta).read_text(encoding='utf-8'))
    saved['reading'] += '\nThis is safe to merge.'
    sf.baseline_path(meta).write_text(json.dumps(saved), encoding='utf-8')
    ok, why = sf.check_one(meta)
    assert ok is False and 'refused' in why


def test_apply_appends_the_change_and_touches_nothing_else(tmp_path):
    target = tmp_path / DEFECTS['target']
    target.parent.mkdir(parents=True)
    target.write_bytes(b'.a{color:red;}\n')
    (tmp_path / 'other.css').write_bytes(b'.b{}\n')
    sf.apply(DEFECTS, tmp_path)
    assert target.read_bytes() == b'.a{color:red;}\n' + sf.change_text(DEFECTS).encode()
    assert (tmp_path / 'other.css').read_bytes() == b'.b{}\n'
    with pytest.raises(FileNotFoundError):
        sf.apply(DEFECTS, tmp_path / 'nowhere')


def test_the_change_hash_ignores_the_line_ends_a_checkout_gives_it(tmp_path):
    meta = scratch(tmp_path, CLEAN)
    before = sf.change_sha(meta)
    p = Path(meta['_path']) / meta['change']
    p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
    assert sf.change_sha(meta) == before


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_every_recorded_reading_still_satisfies_its_fixture(meta):
    ok, why = sf.check_one(meta)
    assert ok is True, why
    base = sf.load_baseline(meta)
    assert base['satisfied'] is True and base['pr'] and base['head']
