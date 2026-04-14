# runners/__init__.py
from .base_runner import BaseRunner
from .standard_runner import StandardRunner

RUNNER_MAP = {
    "auto": StandardRunner,
}

__all__ = ["BaseRunner", "RUNNER_MAP"]