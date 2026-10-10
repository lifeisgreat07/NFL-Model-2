"""The home page's words (Stage 68 item 18a: the audit's U5, U6, U7, U8, U10).

Run with: pytest tests/test_home_words.py -v
"""
from src.site import home

PAGE = (home.TEMPLATE / 'page.html').read_text(encoding='utf-8')
CSS = (home.TEMPLATE / 'home.css').read_text(encoding='utf-8')


def test_the_hero_says_who_runs_this():
    assert '<p class="home-who">A free, open personal project: no tips for sale and no betting advice' in PAGE


def test_the_footnote_is_for_a_visitor_not_the_build():
    assert '<p class="home-foot">Times are shown in your time zone.</p>' in PAGE
    assert 'the files the last build read' not in PAGE


def test_can_i_check_the_picks_links_the_history():
    faq = PAGE[PAGE.index('<summary>Can I check the picks?</summary>'):]
    faq = faq[:faq.index('</details>')]
    assert 'href="https://github.com/lifeisgreat07/NFL-Model-2/commits/main/predictions"' in faq


def test_the_footer_says_which_sport_its_pages_are():
    foot = PAGE[PAGE.index('<footer class="home-links">'):PAGE.index('</footer>')]
    for line in foot.splitlines():
        if 'href="nfl/' in line:
            assert 'NFL' in line, line


def test_one_rule_at_the_page_foot():
    assert '.home-faq details:last-of-type{ border-bottom:0; }' in CSS
