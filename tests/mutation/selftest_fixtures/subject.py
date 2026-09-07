"""A deliberately trivial module, existing only so the mutation runner can be
tested against something whose behaviour is not in question.

Mutating real source to test the harness would confuse two questions -- is the
guard good, and is the harness honest. This answers only the second.
"""


def is_positive(n):
    return n > 0


def unguarded(n):
    """Nothing asserts anything about this. A mutation here must SURVIVE,
    which is how the runner proves it can report a failure at all."""
    return n * 2
