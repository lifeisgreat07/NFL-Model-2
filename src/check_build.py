"""
Refuse to publish a dashboard whose data is missing.

The case this exists for: Team Deep-Dive rendered empty for all 32 teams for
months, because its history file was in the wrong directory and the loader
returned `{}` without a word. The page built, deployed and looked fine until
someone opened that tab. The Pages workflow already refused a page with an
unfilled `__PLACEHOLDER__`; a placeholder filled with nothing got through.

So this reads the BUILT page, pulls out every data payload the generator
wrote into it, and checks each one holds what its page needs:

  ERROR    a payload is missing from the page, or empty where the page has
           nothing to show without it: 32 teams, saved weeks each with games,
           a latest week that is one of them, 32 teams of history, a version
           history, a model version, the calibration table, the audit log.
           Any `__PLACEHOLDER__` left unfilled is an error too.
  WARNING  no printable picks sheets. The generator skips PDFs on purpose
           when reportlab is unavailable, and the download control hides
           itself, so the page is still honest.

Season Accuracy may hold no weeks: before the first graded week there is
genuinely nothing to show, and the page says so. It must still be present,
with its weeks list, or the page has nothing to say that with.

Run after the generator, before publishing:

    python src/generate_dashboard.py && python src/check_build.py index.html
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_quality import NFL_TEAMS, Report  # noqa: E402

#: The page's JavaScript names for what generate_dashboard.main() writes.
PAYLOADS = ('agentLog', 'versionHistory', 'modelVersion', 'teams', 'playoffMeta',
            'weeks', 'latestWeekKey', 'picksPdfs', 'accuracy', 'teamHistory',
            'calibration')

PLACEHOLDER_RE = re.compile(r'__[A-Z0-9_]+__')


def extract(html):
    """{name: value} for every payload found; a payload absent from the page
    is absent from the dict. Reads the JSON the generator wrote straight after
    `const <name> = `, so a payload is parsed exactly as the browser would."""
    decoder = json.JSONDecoder()
    found = {}
    for name in PAYLOADS:
        m = re.search(r'\bconst ' + re.escape(name) + r' = ', html)
        if not m:
            continue
        try:
            found[name], _ = decoder.raw_decode(html, m.end())
        except json.JSONDecodeError as exc:
            found[name] = ValueError(f'not valid JSON: {exc.msg}')
    return found


def check(html):
    report = Report()
    left = sorted(set(PLACEHOLDER_RE.findall(html)))
    if left:
        report.errors.append(f'unfilled template placeholders: {left}')

    data = extract(html)
    for name in PAYLOADS:
        if name not in data:
            report.errors.append(f'the page has no `{name}` payload at all')
        elif isinstance(data[name], ValueError):
            report.errors.append(f'`{name}` is {data[name]}')
    ok = {k: v for k, v in data.items() if not isinstance(v, ValueError)}

    def need(name, test, what):
        if name in ok and not test(ok[name]):
            report.errors.append(f'`{name}` {what}')

    need('teams', lambda v: isinstance(v, list) and {t.get('team') for t in v} == NFL_TEAMS,
         'does not hold the 32 teams (Power Ratings would be short or empty)')
    need('weeks', lambda v: isinstance(v, dict) and len(v) > 0,
         'holds no saved weeks (the Week Board and My Picks would be empty)')
    need('weeks', lambda v: not isinstance(v, dict) or all(w.get('games') for w in v.values()),
         'lists a week with no games in it')
    need('latestWeekKey', lambda v: v in ok.get('weeks', {}),
         'is not one of the saved weeks, so the board opens on nothing')
    need('teamHistory', lambda v: isinstance(v, dict)
         and set(v.get('timeline') or {}) == NFL_TEAMS
         and all(v['timeline'][t] for t in NFL_TEAMS),
         'does not hold a history for each of the 32 teams (Team Deep-Dive would be blank)')
    need('accuracy', lambda v: isinstance(v, dict) and isinstance(v.get('weeks'), list),
         'has no weeks list for Season Accuracy to read')
    need('versionHistory', lambda v: isinstance(v, list) and len(v) > 0,
         "is empty (What's Changed would be blank)")
    need('modelVersion', lambda v: isinstance(v, str) and v.strip() != '',
         'is empty')
    need('calibration', lambda v: isinstance(v, dict) and v.get('models'),
         'is missing (the reliability diagram would be omitted)')
    need('agentLog', lambda v: isinstance(v, dict) and isinstance(v.get('audits'), list),
         "is missing (Checking the AI's work would say no audits were ever recorded)")

    if 'picksPdfs' in ok and not ok['picksPdfs']:
        report.warnings.append('no printable picks sheets were built; the download control will hide itself')
    return report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0] if argv else 'index.html')
    if not path.is_file() or path.stat().st_size == 0:
        print(f'ERROR: {path} is missing or empty')
        return 1
    report = check(path.read_text(encoding='utf-8'))
    for line in report.lines():
        print(line)
    if report.ok:
        print(f'{path}: every payload is present and non-empty')
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
