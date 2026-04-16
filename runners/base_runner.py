# runners/base_runner.py
import os
from abc import ABC, abstractmethod
from typing import Any

class BaseRunner(ABC):
    """
    すべての実行モードの基底となる抽象クラス。
    """
    
    def __init__(self, config: Any) -> None:
        self.config = config
    
    @abstractmethod
    def run(self) -> None:
        pass