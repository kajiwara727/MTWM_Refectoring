# runners/base_runner.py
import os
from abc import ABC, abstractmethod
from typing import Any
from visualization import get_visualizer  # Factory関数をインポート

class BaseRunner(ABC):
    """
    すべての実行モードの基底となる抽象クラス。
    """
    
    def __init__(self, config: Any) -> None:
        self.config = config
    
    @abstractmethod
    def run(self) -> None:
        pass

    def visualize(self, mode: str, data: Any, output_filename: str, title: str) -> None:
        """
        可視化インスタンスの生成から描画・保存までを一括で行う共通メソッド。
        """
        # 出力先のディレクトリ決定
        output_dir = "output/dfmm_plots" if mode == 'dfmm' else "output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        # Factory経由で適切なVisualizerを取得
        visualizer = get_visualizer(mode=mode, data=data)
        
        print(f"  [Visualizing] {title} を出力中: {output_path}")
        visualizer.draw(output_path=output_path, title=title)