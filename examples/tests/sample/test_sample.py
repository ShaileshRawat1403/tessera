"""Sample test file exercising the tests-pack analyzer (not run by tessera's suite)."""

import pytest


def test_passes_with_assert():
    assert 1 + 1 == 2


def test_no_assertions():
    # no assertion: silently passes
    value = 2 + 2
    str(value)


@pytest.mark.skip(reason="not ready")
def test_skipped():
    assert False


@pytest.mark.xfail
def test_expected_fail():
    assert False


@pytest.mark.parametrize("n", [1, 2, 3])
def test_parametrized(n):
    assert n > 0


class TestThing:
    def test_method_with_assert(self):
        self.assertEqual(1, 1)
