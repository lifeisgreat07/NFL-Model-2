"""
The pipeline's log (Stage 32 item 17, from the 2026-09-29 re-audit).

The weekly update, grading, the weekend refresh and the drift check used
print(). They now log through the standard library, so each line carries a
level (a WARNING line is logged as a warning) and a caller can raise, lower
or redirect it without editing the scripts.

What they print is unchanged, deliberately, because it is read:
src/pipeline/weekly_summary.py parses the weekly run's log, and the workflows tee it.
So the handler writes the bare message, with print's newline, to stdout.

Two details keep it identical to print:
- The stream is looked up when a line is written, not when the handler is
  made. A StreamHandler keeps the stream it was given, so a script that
  swaps sys.stdout (pytest's capsys does, and so does anything that
  redirects a run's output) would otherwise keep writing to the old one.
- A line that cannot be written raises, as print did. logging's default is
  to report the error to stderr and carry on, which would drop the line from
  the log without failing the run.
"""
import logging
import sys


class _StdoutHandler(logging.StreamHandler):
    """A StreamHandler whose stream is always the current sys.stdout."""

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value):
        # StreamHandler.__init__ assigns a stream; there is nothing to keep.
        pass

    def handleError(self, record):
        raise


def get_logger(name):
    """The logger a pipeline module logs through: INFO and up, the bare
    message, to the current stdout, and not passed up to the root logger
    (which would print it a second time wherever the root has a handler)."""
    log = logging.getLogger(f'nfl.{name}')
    if not any(isinstance(h, _StdoutHandler) for h in log.handlers):
        handler = _StdoutHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log
