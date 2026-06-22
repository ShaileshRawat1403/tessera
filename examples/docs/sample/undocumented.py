# no module docstring on purpose


def subtract(a, b):
    return a - b


class Widget:
    def render(self):
        return "<widget>"

    def _private_helper(self):
        # private: should not be required to have a docstring
        return 1
