"""The Pages deploy rebuilds on a push to anything a page is built from (Stage 68 item 9).

deploy-pages.yml watched data/nfl, predictions/nfl and results/nfl only,
so a hand-pushed fix to the NHL's or NBA's files, or to a backtest under
experiments/ that the NHL and NBA pages print, never redeployed. The daily
runs reach the builder through workflow_run (their GITHUB_TOKEN pushes
trigger nothing); this is for every other push.

Run with: pytest tests/test_deploy_paths.py -v
"""
import re
from pathlib import Path

WF = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'deploy-pages.yml'
#: Every top-level folder some page's build reads.
READ = ('src', 'data', 'predictions', 'results', 'experiments', 'assets')


def watched():
    text = WF.read_text(encoding='utf-8').replace('\r\n', '\n')
    push = text[text.index('  push:\n'):text.index('  workflow_run:')]
    return re.findall(r"^\s+- '([^']+)'$", push, re.M)


def test_every_folder_a_page_reads_is_watched_whole():
    paths = watched()
    missing = [r for r in READ if f'{r}/**' not in paths]
    assert not missing, f'not watched as whole folders: {missing}'


def test_no_sport_folder_is_watched_alone():
    narrow = [p for p in watched() if re.match(r'(data|predictions|results|experiments)/[a-z]+/', p)]
    assert not narrow, f'a sport-only path hides the rest of its folder: {narrow}'
