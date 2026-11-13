"""
Stage 83 item 6: every credential the unattended runs depend on is in
.github/credentials.json with its expiry date, and an issue opens 30 days
before one expires.

Run with: pytest tests/test_credentials.py -v
"""
import json
import re
from datetime import date
from pathlib import Path

import pytest

from src.core import credentials as cr

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / '.github' / 'credentials.json'
WORKFLOWS = ROOT / '.github' / 'workflows'
ROW = {'name': 'T', 'kept_in': 'a secret', 'used_by': 'x.yml', 'breaks': 'x', 'expires': '2027-01-31',
       'expires_basis': 'made 2026-01-31, one year', 'renew': 'make another'}


def doc(**over):
    return {'credentials': [{**ROW, **over}]}


def committed():
    return json.loads(REGISTER.read_text(encoding='utf-8'))


# --- when it warns --------------------------------------------------------------------------

def test_a_credential_warns_from_30_days_out_and_not_before():
    assert cr.due(doc(), date(2027, 1, 1)) == [(doc()['credentials'][0], 30)]
    assert cr.due(doc(), date(2026, 12, 31)) == [], '31 days out is not yet due'


def test_an_expired_credential_keeps_warning():
    (row, left), = cr.due(doc(), date(2027, 2, 3))
    assert left == -3
    assert 'expired 3 day(s) ago' in cr.report([(row, left)])


def test_the_report_says_what_breaks_and_how_to_renew():
    text = cr.report(cr.due(doc(), date(2027, 1, 20)))
    for want in ('### T: expires in 11 day(s) (2027-01-31)', '- Without it: x', '- To renew: make another',
                 '- How the date is known: made 2026-01-31, one year', 'update `expires`'):
        assert want in text, want


# --- what an entry must say ------------------------------------------------------------------

@pytest.mark.parametrize('field', cr.REQUIRED)
def test_an_entry_missing_a_field_is_refused(field):
    with pytest.raises(cr.CredentialsError):
        cr.entries(doc(**{field: ''}))


def test_a_date_that_is_not_a_date_is_refused():
    with pytest.raises(cr.CredentialsError):
        cr.entries(doc(expires='next September'))


def test_an_empty_register_is_refused():
    with pytest.raises(cr.CredentialsError):
        cr.entries({'credentials': []})


# --- the command the workflow runs ------------------------------------------------------------

def test_the_command_exits_0_1_or_2_and_writes_the_report(tmp_path):
    reg, out = tmp_path / 'c.json', tmp_path / 'r.md'
    reg.write_text(json.dumps(doc()), encoding='utf-8')
    assert cr.main([str(reg), str(out)], today=date(2026, 6, 1)) == 0 and not out.exists()
    assert cr.main([str(reg), str(out)], today=date(2027, 1, 20)) == 1
    assert '### T: expires in 11 day(s)' in out.read_text(encoding='utf-8')
    reg.write_text('{"credentials": [', encoding='utf-8')
    assert cr.main([str(reg), str(out)], today=date(2027, 1, 20)) == 2
    assert 'cannot be read' in out.read_text(encoding='utf-8')


def test_the_nightly_audit_checks_it_on_mondays_and_alerts():
    wf = (WORKFLOWS / 'nightly-dependency-audit.yml').read_text(encoding='utf-8')
    step = wf[wf.index('- name: Check credential expiry dates'):wf.index('- name: Raise an alert if the job itself failed')]
    assert 'if [ "$(date -u +%u)" != "1" ]; then' in step, 'Mondays, by weekday: cron-job.org dispatches it nightly'
    assert 'python -m src.core.credentials .github/credentials.json credentials-report.md' in step
    assert 'set +e' in step, 'exit 1 means "due", not a failed job'
    assert '--title "A credential expires within 30 days" --body-file credentials-report.md' in step
    assert '--title "Credentials register cannot be read" --body-file credentials-report.md' in step
    assert 'GH_TOKEN: ${{ github.token }}' in step


# --- the committed register --------------------------------------------------------------------

def test_the_committed_register_reads():
    rows = cr.entries(committed())
    assert {r['name'] for r in rows} >= {'CLAUDE_CODE_OAUTH_TOKEN', 'cron-job.org GitHub token'}


def secrets_read():
    """secrets.NAME -> the workflow files that read it."""
    out = {}
    for wf in sorted(WORKFLOWS.glob('*.yml')):
        for name in set(re.findall(r'secrets\.([A-Za-z_][A-Za-z0-9_]*)', wf.read_text(encoding='utf-8'))):
            out.setdefault(name, set()).add(wf.name)
    out.pop('GITHUB_TOKEN', None)
    return out


def test_every_secret_a_workflow_reads_is_registered():
    """A postcondition over the workflows: a new secret with no expiry date
    on record fails here, not on the day it stops working."""
    names = {r['name'] for r in committed()['credentials']}
    used = secrets_read()
    assert used, 'no secret found in any workflow -- re-anchor this guard'
    assert set(used) <= names, f'not in .github/credentials.json: {sorted(set(used) - names)}'


def test_each_secrets_entry_names_every_workflow_that_reads_it():
    by_name = {r['name']: r for r in committed()['credentials']}
    for name, files in secrets_read().items():
        missing = sorted(f for f in files if f not in by_name[name]['used_by'])
        assert not missing, f'{name}: used_by does not name {missing}'
