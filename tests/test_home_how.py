"""Stage 90 item 2: How it works, from data to rating, chance, lock, grade and
audit, on the home page, each step but the first linked to where a reader can
check it.

Run with: pytest tests/test_home_how.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
NFL = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')


def steps():
    block = re.search(r'<ol class="home-steps">(.*?)</ol>', PAGE, re.S).group(1)
    return re.findall(r'<li>.*?<b>(.*?)</b>(.*?)</span></li>', block)


def test_six_steps_from_data_to_audit_in_order():
    assert [title for title, _ in steps()] == ['From public data', 'A rating for every team', 'A chance for every game',
                                              'Locked in public', 'Graded after', 'Checked by agents']


def test_every_step_after_the_data_links_to_a_place_that_exists():
    links = [re.search(r'href="([^"]+)"', body) for _, body in steps()]
    assert links[0] is None
    for m in links[1:]:
        href = m.group(1)
        if href.startswith('nfl/#'):
            assert f'id="page-{href[5:]}"' in NFL, f'{href}: the NFL page has no such section'
        elif href.startswith('#'):
            assert f'id="{href[1:]}"' in PAGE, f'{href}: the home page has no such section'
        else:
            assert href == 'https://github.com/lifeisgreat07/NFL-Model-2/commits/main/predictions', href
