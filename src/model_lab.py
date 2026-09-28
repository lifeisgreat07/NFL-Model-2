"""The Model Lab's records, as one list the page can be built from (Stage 18).

Two sources, and nothing typed in between them:

- experiments/legacy/rows.json -- the 46 rows the page carried before Stage 18,
  moved there once, verbatim. Their text is the page's own HTML; only the
  mapping onto the five decisions is new.
- experiments/<stage>/results/<id>.json -- every pre-registered answer from
  Stage 5 on, read as it was committed, plus each registry entry marked
  DEFERRED (a registered question that was deliberately not asked has no
  result file, and leaving it off would hide a decision).

THE FIVE DECISIONS are the project's own (CLAUDE.md, "Non-negotiable
methodology"): ACCEPT, REJECT, INCONCLUSIVE, DEFERRED, CONFIRMED FINDING.
Every entry carries one, and keeps the label it was first given beside it, so
a mapping can be checked rather than trusted. Leakage is a separate flag, not a
sixth decision: a result invalidated by leakage still has to say what happens
to the question.

Every figure a result entry carries is copied from its file here, not
retyped; tests/test_model_lab.py holds each one to the file it came from.

    python src/model_lab.py      # prints each entry's id, decision and headline
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = ROOT / 'experiments'
LEGACY = EXPERIMENTS / 'legacy' / 'rows.json'

DECISIONS = ('ACCEPT', 'REJECT', 'INCONCLUSIVE', 'DEFERRED', 'CONFIRMED FINDING')

#: A registered answer's stored label, onto the five decisions. A label not
#: here is an error, never a guess: the registry tests compute these labels,
#: and a new one means a rule nobody has mapped yet.
RESULT_DECISION = {
    'ACCEPT': 'ACCEPT',
    'REJECT': 'REJECT',
    'INCONCLUSIVE': 'INCONCLUSIVE',
    'DEFERRED': 'DEFERRED',
    # Failed the validation screen, so it never reached confirmation: the
    # candidate was no better where it was tuned, which is a rejection.
    'NOT ADVANCED': 'REJECT',
    # A screen (Stage 6's N1) whose registered rule was not met.
    'FAIL': 'REJECT',
    # Q0: the interval on the gap contains zero. Under the project's rule a
    # result counts only when its interval excludes zero, so this is not a
    # confirmed finding of "no gap" -- it is a gap too small to measure.
    'NO MEASURABLE GAP': 'INCONCLUSIVE',
}


def _stage_name(path):
    """'stage5' -> 'Stage 5'."""
    name = path.name
    return 'Stage ' + name[len('stage'):] if name.startswith('stage') else name


def _rel(path):
    """Repository-relative when it can be, so a source reads the same on any
    machine; as given otherwise (a test's temporary folder)."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def headline(result):
    """(metric dict, or None) for one result file: the registered comparison's
    proper-scoring-rule difference and its interval, from the furthest step
    the question reached.

    Confirmation when it got there, else the validation screen. Q0 is a
    measurement over all four seasons, reported for Model A. N1 is scored on
    mean squared error of a quarterback's next game, with a cluster-bootstrap
    interval. A difference is always candidate minus incumbent, so a negative
    number favours the candidate. R1 is the exception: a correlation across
    referees, which only an interval wholly above zero passes, so it carries
    its own note in place of that sentence."""
    if 'persistence' in result:
        block = result['persistence']
        return {'metric': 'weighted correlation',
                'of': "a referee's home/away penalty gap, from one period to the next",
                'diff': block['weighted_corr'], 'ci': block['corr_ci_95'], 'ci_level': 0.95,
                'seasons': result['inputs']['seasons'], 'n': block['n_referees'], 'n_of': 'referees',
                'step': 'screen', 'model': None,
                'note': 'The screen needed the whole interval above zero.'}
    if 'candidate_minus_control' in result:
        block, val = result['candidate_minus_control'], result['validation']
        return {'metric': 'mean squared error', 'of': "a quarterback's next-game EPA per dropback",
                'diff': block['mse_diff'], 'ci': block['mse_ci_95'], 'ci_level': 0.95,
                'seasons': val['seasons'], 'n': val['n_qb_games'], 'n_of': 'quarterback games',
                'step': 'screen', 'model': None}
    if 'model_a' in result and 'validation' not in result:
        block = result['model_a']
        return {'metric': 'log loss', 'of': 'game winners', 'diff': block['log_loss_diff'],
                'ci': block['log_loss_ci'], 'ci_level': block['ci_level'],
                'seasons': block['seasons'], 'n': block['n_games'], 'n_of': 'games',
                'step': 'measurement', 'model': 'Model A'}
    step = 'confirmation' if result.get('confirmation') else 'validation'
    block = result[step]
    model = result.get('registry_entry', {}).get('decision_model')
    return {'metric': 'log loss', 'of': 'game winners', 'diff': block['log_loss_diff'],
            'ci': block['log_loss_ci'], 'ci_level': block['ci_level'],
            'seasons': block['seasons'], 'n': block['n_games'], 'n_of': 'games',
            'step': step, 'model': {'model_a': 'Model A', 'model_b': 'Model B'}.get(model)}


def result_entries(experiments=EXPERIMENTS):
    """One entry per results file, then one per registry entry marked
    DEFERRED, stage by stage in registration order."""
    out = []
    for stage in sorted(p for p in experiments.glob('stage*') if p.is_dir()):
        registry = json.loads((stage / 'registry.json').read_text(encoding='utf-8'))
        for entry in registry['hypotheses']:
            path = stage / 'results' / f"{entry['id']}.json"
            if path.exists():
                result = json.loads(path.read_text(encoding='utf-8'))
                label = result['decision']
                if label not in RESULT_DECISION:
                    raise ValueError(f'{_rel(path)}: no decision is mapped for {label!r}')
                out.append({'id': entry['id'], 'stage': _stage_name(stage),
                            'title': entry['title'], 'question': entry.get('question'),
                            'label': label, 'decision': RESULT_DECISION[label],
                            'leakage': False, 'headline': headline(result),
                            'source': _rel(path)})
            elif entry.get('status') == 'DEFERRED':
                out.append({'id': entry['id'], 'stage': _stage_name(stage),
                            'title': entry['title'], 'question': entry.get('question'),
                            'label': 'DEFERRED', 'decision': 'DEFERRED', 'leakage': False,
                            'headline': None, 'reason': entry.get('reason'),
                            'source': _rel(stage / 'registry.json')})
    return out


def legacy_entries(path=LEGACY):
    rows = json.loads(path.read_text(encoding='utf-8'))['rows']
    return [dict(r, stage=None, headline=None, source=_rel(path)) for r in rows]


def entries(experiments=EXPERIMENTS, legacy=LEGACY):
    """Registered answers first, newest stage first, then the moved-in rows in
    the order the page showed them."""
    results = result_entries(experiments)
    stages = sorted({e['stage'] for e in results}, key=lambda s: int(s.split()[-1]), reverse=True)
    ordered = [e for s in stages for e in results if e['stage'] == s]
    return ordered + legacy_entries(legacy)


def main():
    for e in entries():
        h = e.get('headline')
        figure = (f"{h['metric']} {h['diff']:+.4f} [{h['ci'][0]:+.4f}, {h['ci'][1]:+.4f}] "
                  f"at {h['ci_level']:.1%}" if h else '')
        print(f"{e['id']:>4}  {e['decision']:<18} {e['label']:<24} {figure}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
