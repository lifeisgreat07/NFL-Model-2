"""Readers every sport shares. Each one takes the sport whose folder it reads."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_ratings(sport):
    return json.loads((ROOT / 'data' / sport / 'ratings.json').read_text(encoding='utf-8'))


def load_results(sport='nfl'):
    return json.loads((ROOT / 'data' / sport / 'results.json').read_text(encoding='utf-8'))
