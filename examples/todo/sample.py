"""Sample module sprinkled with code markers."""


def process(items):
    # TODO(sam): refactor this loop to use a comprehension
    out = []
    for it in items:
        out.append(it)
    return out


def risky(value):
    # FIXME: this crashes on empty input
    return value[0]


def workaround():
    # HACK temporary shim until the upstream fix lands
    return 42


def later():
    # NOTE: revisit after v2 ships
    # TODO
    return None
