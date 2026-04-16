from typing import Any, Optional
from .dfmm_visualizer import DFMMVisualizer
from .problem_visualizer import MTWMProblemVisualizer
from .result_visualizer import MTWMResultVisualizer
from .config import VisualizerConfig

def get_visualizer(mode: str, data: Any, config: Optional[type] = None):
    """
    指定されたモードに応じて適切なVisualizerのインスタンスを生成して返す。
    
    Args:
        mode (str): 'dfmm', 'problem', 'result' のいずれか
        data (Any): 可視化対象のデータ (Dict, MTWMProblem, ソリューション結果など)
        config (type, optional): 独自の設定クラス。指定がない場合はデフォルトのVisualizerConfigを使用。
        
    Returns:
        BaseVisualizer: 生成されたVisualizerのインスタンス
        
    Raises:
        ValueError: 未知のモードが指定された場合
    """
    target_config = config if config else VisualizerConfig

    if mode == 'dfmm':
        return DFMMVisualizer(data, target_config)
    elif mode == 'problem':
        return MTWMProblemVisualizer(data, target_config)
    elif mode == 'result':
        return MTWMResultVisualizer(data, target_config)
    else:
        raise ValueError(f"Unknown visualizer mode: '{mode}'")