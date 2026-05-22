from demo_project.core import describe


def test_describe_names_compile_loop() -> None:
    assert describe() == "repo -> .microcosm"
