# visualization/__init__.py
from .factory import get_visualizer
from .config import VisualizerConfig

# 外部モジュールにはFactory関数と設定クラスのみを公開する
__all__ = ["get_visualizer", "VisualizerConfig"]