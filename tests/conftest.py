"""Keep pytest temporary output inside the ignored workspace directory."""

from pathlib import Path


def pytest_configure(config):
    # A fresh clone has no tmp/ parent for pytest's configured --basetemp.
    (Path(__file__).resolve().parents[1] / "tmp").mkdir(exist_ok=True)
