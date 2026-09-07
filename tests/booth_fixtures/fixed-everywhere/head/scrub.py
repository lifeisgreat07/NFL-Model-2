"""Drop artifacts whose only change is a build stamp."""


def is_stamp_only(before, after):
    """True when two artifact texts differ only in their build stamp line."""
    strip = lambda text: [
        line for line in text.splitlines() if not line.startswith('built:')
    ]
    return strip(before) == strip(after)
