# Notes

Two sports live in this repository, the NFL and the NHL. Each sport's page is
built from its own folder under `data/` and nothing else: an NHL page that
shows an NFL number is the one mistake a multi-sport site cannot make quietly,
because both leagues use the same team-and-score shapes and nothing looks wrong.

`core/data.py` holds the readers every sport shares. A caller passes its sport.

Build a page with `python -m sports.nfl.site` or `python -m sports.nhl.site`;
each writes `out/<sport>.html`.
