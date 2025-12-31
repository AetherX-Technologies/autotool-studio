from autotool_system.cli import main


def test_cli_status() -> None:
    assert main(["status"]) == 0


def test_cli_version() -> None:
    assert main(["version"]) == 0
