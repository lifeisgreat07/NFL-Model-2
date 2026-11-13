"""The dashboard's script is kept as parts along its page sections (Stage 87 item 4).

src/dashboard/app.js was one file of some five thousand lines. It is six parts,
app_controls.js to app_pages.js, which page.html includes in order where it
included app.js, so the joined template is unchanged. Tests read the joined
script through src.core.template_parts.APP_SCRIPT. Every mutation case names
its part (steps two and three); tests/mutation/corpus.py still resolves a case
naming src/dashboard/app.js to the one part holding its anchor, but no case in
the corpus may rely on that.

Run with: pytest tests/test_app_parts.py -v
"""
import json
import sys
from pathlib import Path

from src.core import template_parts as tp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests' / 'mutation'))
import corpus as mc

DASH = ROOT / 'src' / 'dashboard'


def test_app_js_is_gone_and_its_parts_are_included_in_order():
    assert not (DASH / 'app.js').exists(), 'app.js came back beside its parts'
    names = [p.name for p in tp.app_parts()]
    assert names == ['app_controls.js', 'app_ratings.js', 'app_board.js', 'app_accuracy.js', 'app_team.js',
                     'app_pages.js']
    shell = (DASH / 'page.html').read_text(encoding='utf-8').replace('\r\n', '\n')
    assert '<script>\n' + ''.join(f'{{% include "{n}" %}}\n' for n in names) + '</script>' in shell


def test_each_part_opens_on_its_own_section():
    banners = {'app_ratings.js': '/* ---------- Power Ratings ---------- */',
               'app_board.js': '/* ---------- Week Board ---------- */',
               'app_accuracy.js': '/* ---------- What actually happened at this confidence level ----------',
               'app_team.js': '/* ---------- Team Deep-Dive ----------',
               'app_pages.js': '/* ---------- Changelog ---------- */'}
    for name, banner in banners.items():
        assert (DASH / name).read_text(encoding='utf-8').splitlines()[0] == banner, name


def test_the_joined_script_is_the_parts_in_order_and_sits_in_the_template():
    script = tp.APP_SCRIPT.read_text(encoding='utf-8')
    assert script == ''.join(p.read_text(encoding='utf-8') for p in tp.app_parts())
    assert script in tp.read_template()


def test_the_corpus_knows_the_same_parts():
    assert mc.SPLIT['src/dashboard/app.js'] == [p.relative_to(ROOT).as_posix() for p in tp.app_parts()]


def test_a_case_naming_app_js_resolves_to_the_part_holding_its_anchor():
    board = (DASH / 'app_board.js').read_text(encoding='utf-8').replace('\r\n', '\n')
    anchor = '/* ---------- Week Board ---------- */\n'
    assert board.count(anchor) == 1
    assert mc.resolve_target('src/dashboard/app.js', anchor) == 'src/dashboard/app_board.js'
    assert mc.resolve_target('src/core/csp.py', anchor) == 'src/core/csp.py'


def test_an_anchor_once_in_each_of_two_parts_is_not_given_to_either(tmp_path, monkeypatch):
    """Resolving to the first part would mutate one copy and leave the other: the case names the whole file,
    and its count is 2, which the anchor check refuses."""
    (tmp_path / 'a.js').write_text('one();\nshared();\n', encoding='utf-8')
    (tmp_path / 'b.js').write_text('shared();\ntwo();\n', encoding='utf-8')
    monkeypatch.setattr(mc, 'REPO_ROOT', tmp_path)
    monkeypatch.setattr(mc, 'SPLIT', {'whole.js': ['a.js', 'b.js']})
    assert mc.resolve_target('whole.js', 'one();') == 'a.js'
    assert mc.resolve_target('whole.js', 'shared();') == 'whole.js'
    assert mc.anchor_occurrences({'id': 'x', 'target': 'whole.js', 'find': 'shared();'})[0] == 2


def test_an_anchor_in_two_parts_or_none_stays_on_app_js_and_is_counted_across_them():
    twice = 'function '
    assert mc.resolve_target('src/dashboard/app.js', twice) == 'src/dashboard/app.js'
    count, _, _ = mc.anchor_occurrences({'id': 'x', 'target': 'src/dashboard/app.js', 'find': twice})
    assert count == sum((ROOT / p).read_text(encoding='utf-8').count(twice) for p in mc.SPLIT['src/dashboard/app.js'])
    assert mc.resolve_target('src/dashboard/app.js', 'no such text anywhere 0x51f') == 'src/dashboard/app.js'
    count, _, _ = mc.anchor_occurrences({'id': 'x', 'target': 'src/dashboard/app.js',
                                         'find': 'no such text anywhere 0x51f'})
    assert count == 0


def test_no_mutation_case_names_the_whole_file_any_more():
    """Stage 87 item 4, step three: each case names its part itself, read from the
    case files as written, before load_corpus resolves anything. A case aimed at
    app.js would still run, through the resolution, which is why only this sees it."""
    whole = []
    for path in sorted((ROOT / 'tests' / 'mutation' / 'cases').glob('*.json')):
        doc = json.loads(path.read_text(encoding='utf-8'))
        whole += [f"{path.name}: {c['id']}" for c in doc['cases']
                  if c.get('target', doc.get('target')) == 'src/dashboard/app.js']
    assert whole == [], f'{len(whole)} case(s) still name src/dashboard/app.js: {whole[:5]}'


def test_the_old_path_reads_the_joined_script():
    """Checks that list files by path keep naming src/dashboard/app.js and read the joined script."""
    assert tp.read_repo_file('src/dashboard/app.js') == tp.app_script()
    assert tp.read_repo_file('src/dashboard/body.html') == (DASH / 'body.html').read_text(encoding='utf-8')
