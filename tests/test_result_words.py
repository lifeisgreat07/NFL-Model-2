"""One pair of result words on every surface: Correct and Missed (Stage 77 item 26, the 2026-10-13 UI/UX audit's copy row 15).

A graded pick read "Right"/"Wrong" on the NFL's phone rows, "this model was
right/wrong" on the NFL's tick and cross, "correct"/"wrong" in Team
Deep-Dive, "right"/"wrong" in the NHL's and NBA's card result line, and
"1 of 3 right so far" in the NHL's and NBA's day summary, and
"Correct"/"Missed" on the NFL card tag and the NHL's and NBA's rows
(measured 2026-10-14, 390 and 1440 px, both themes). Mark chose Correct and
Missed on 2026-10-14. Prose that explains a result in a sentence ("how often
the pick was right") is not a result label and is left alone.

Run with: pytest tests/test_result_words.py -v
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'nfl': ROOT / 'src' / 'dashboard' / 'app.js',
    'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
    'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js',
}
LABELS = {
    'nfl': ["    : verdict ? ['correct', 'Correct'] : ['incorrect', 'Missed'];",
            "${verdict ? 'Correct' : 'Missed'}</span>",
            "    : (correct ? \"this model's pick: correct\" : \"this model's pick: missed\");",
            "    const mark = c => c === true ? '<span class=\"dive-tick\">correct</span>'\n"
            "      : c === false ? '<span class=\"dive-cross\">missed</span>' : '';"],
    'nhl': ["<b>${s === won ? 'correct' : 'missed'}</b>",
            ", ${right} of ${graded.length} correct so far`;",
            '<th scope="col" class="num">Said, on average</th><th scope="col" class="num">Correct</th>',
            "if(p.result === 'correct') return {text: 'Correct', cls: 'right'};",
            "if(p.result === 'wrong') return {text: 'Missed', cls: 'wrong'};"],
    'nba': ["<b>${s === won ? 'correct' : 'missed'}</b>",
            ", ${right} of ${graded.length} correct so far`;",
            '<th scope="col" class="num">Said, on average</th><th scope="col" class="num">Correct</th>',
            "if(p.result === 'correct') return {text: 'Correct', cls: 'right'};",
            "if(p.result === 'wrong') return {text: 'Missed', cls: 'wrong'};"],
}
# A result label written as a string or between tags, in any case.
OLD = re.compile(r"""(['"`>])(Right|Wrong|right|wrong)(['"`<])""")


@pytest.mark.parametrize('sport', SOURCES)
def test_every_result_label_says_correct_or_missed(sport):
    src = SOURCES[sport].read_text(encoding='utf-8')
    for line in LABELS[sport]:
        assert line in src, f'{sport}: {line.strip()[:60]}'


@pytest.mark.parametrize('sport', SOURCES)
def test_no_label_says_right_or_wrong(sport):
    src = SOURCES[sport].read_text(encoding='utf-8')
    # class names and data values ('right', 'wrong' as a result code) are not labels
    hits = [m.group(0) for m in OLD.finditer(src)
            if not re.search(r"(cls: |result === |class=\"[^\"]*$|\.result\s*===\s*)$", src[max(0, m.start() - 40):m.start() + 1])]
    labels = [h for h in hits if h[1] in 'RW' or h[0] == '>' or h[-1] == '<']
    assert not labels, f'{sport} still prints {labels}'
