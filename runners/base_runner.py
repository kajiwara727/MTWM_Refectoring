import os
from abc import ABC, abstractmethod
from typing import Any

class BaseRunner(ABC):
    """
    すべての実行モード（Standard, Randomなど）の基底となる抽象クラス。
    設定の保持や、出力ディレクトリの生成といった共通インフラ機能を提供します。
    """
    
    def __init__(self, config: Any) -> None:
        """
        Args:
            config: 設定情報（モジュールまたはConfigオブジェクト）
        """
        self.config = config
    
    @abstractmethod
    def run(self) -> None:
        """
        最適化プロセスのメインロジック。
        サブクラス（StandardRunner等）で必ずオーバーライドして実装する必要があります。
        """
        pass