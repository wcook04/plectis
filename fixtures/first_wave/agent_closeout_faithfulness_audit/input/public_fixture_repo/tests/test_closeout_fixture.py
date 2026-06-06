from micro_pkg.arithmetic import add


def test_public_fixture_addition():
    assert add(2, 3) == 5
