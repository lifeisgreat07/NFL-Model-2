"""The page's source as the build fills it, for tests that read its copy.

Model Lab's rows stopped being typed into the template in Stage 18:
generate_dashboard.render_model_lab_rows() writes them in at build time from
src/sports/nfl/model_lab.py. A test that holds a figure in those rows to its data file
has to read what the page will actually carry, so it reads this rather than
the raw template -- which now holds only the placeholder, and against which a
"this figure appears on the page" check would pass or fail for the wrong
reason.
"""
from pathlib import Path

from src.core.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE


def model_lab_rows():
    from src.sports.nfl import generate_dashboard as gd
    from src.sports.nfl import model_lab as ml
    return gd.render_model_lab_rows(ml.entries())


def page_source():
    text = TEMPLATE.read_text(encoding='utf-8')
    assert text.count('__MODEL_LAB_ROWS__') == 1, 'the Model Lab placeholder moved -- re-anchor this helper'
    return text.replace('__MODEL_LAB_ROWS__', model_lab_rows())
