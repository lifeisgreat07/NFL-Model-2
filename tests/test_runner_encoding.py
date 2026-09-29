"""The mutation runner reads pytest's report as UTF-8 on every machine.

It read the child's output in the locale codec. On markys that is cp1252,
and on 2026-09-28 one case's failure text carried byte 0x90, which cp1252
cannot decode: the runner crashed instead of reporting the case, and runs
had to be made with PYTHONUTF8=1 set by hand. The runner now asks the child
for UTF-8 and decodes UTF-8, replacing anything undecodable.

The first test runs the runner's own _run_tests() on a failing test whose
report holds characters outside cp1252, so on a cp1252 machine it fails
without the fix; the second holds the call's arguments on every machine.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests' / 'mutation'))
import runner  # noqa: E402

FIXTURE = '''
def test_reports_text_outside_cp1252():
    assert "\\u2014 \\u0444 \\u4e2d \\u0090" == ""
'''


def test_a_report_outside_the_locale_codec_is_read_not_crashed_on(tmp_path):
    f = tmp_path / 'test_encoding_fixture.py'
    f.write_text(FIXTURE, encoding='utf-8')
    code, failed, out = runner._run_tests(str(f))
    assert code != 0
    assert failed == {'test_reports_text_outside_cp1252'}, out[-500:]
    assert '—' in out, 'the report was not decoded as UTF-8'


def test_the_child_is_asked_for_utf8_and_read_as_utf8():
    src = (ROOT / 'tests' / 'mutation' / 'runner.py').read_text(encoding='utf-8')
    fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == '_run_tests')
    call = next(n for n in ast.walk(fn) if isinstance(n, ast.Call) and getattr(n.func, 'attr', '') == 'run')
    kw = {k.arg: getattr(k.value, 'value', None) for k in call.keywords}
    assert kw.get('encoding') == 'utf-8' and kw.get('errors') == 'replace', kw
    assert "'PYTHONIOENCODING': 'utf-8'" in ast.get_source_segment(src, fn)
