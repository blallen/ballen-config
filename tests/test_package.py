import ballen_config


def test_package_exposes_version() -> None:
    """Consumers can read a non-empty package version at runtime."""
    assert ballen_config.__version__
