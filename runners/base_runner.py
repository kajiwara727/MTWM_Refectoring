from abc import ABC, abstractmethod
from typing import Any, List
from core.models import Target
from core import apply_auto_factors
from utils.io_manager import create_experiment_dir
from utils.exporters import ReportExporter, JsonExporter, TextExporter

class BaseRunner(ABC):
    def __init__(self, config: Any) -> None:
        self.config = config
        # エクスポーターの登録
        self.exporters: List[ReportExporter] = [
            JsonExporter(),
            TextExporter()
        ]
    def prepare_targets(self, targets: List[Target]) -> List[Target]:
        """ターゲットにミキサーサイズに応じた前処理（factor分割）を適用する"""
        return apply_auto_factors(targets, self.config.max_mixer_size)

    def create_session_dir(self, settings_summary: str) -> str:
        """I/Oマネージャーに委譲してセッションディレクトリを作成"""
        return create_experiment_dir(self.config.base_output_dir, self.config.runner_mode, settings_summary)

    def save_reports(self, session_dir: str, input_data: dict, output_data: dict) -> None:
        """登録された全てのエクスポーターを使用してレポートを保存する"""
        for exporter in self.exporters:
            exporter.export(session_dir, input_data, output_data)

    @abstractmethod
    def run(self) -> dict:
        """シミュレーションを実行し、結果の辞書を返す"""
        pass

    @abstractmethod
    def visualize(self, result_data: dict) -> None:
        """実行結果（runの戻り値）をもとに、各ランナー固有の可視化を行う"""
        pass