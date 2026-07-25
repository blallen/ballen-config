import ballen_config


def test_package_exposes_version() -> None:
    assert ballen_config.__version__ == "0.1.0"
