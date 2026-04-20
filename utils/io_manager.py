# utils/io_manager.py
import json
import os
from datetime import datetime
from dataclasses import is_dataclass, asdict
from core.models import NodeAddress

class MTWMEncoder(json.JSONEncoder):
    """データクラスやNodeAddressをJSON化するための共通エンコーダー"""
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, NodeAddress):
            return f"({o.target_id}, {o.level}, {o.index})"
        return super().default(o)

def create_experiment_dir(base_dir: str, mode: str, settings_summary: str) -> str:
    """タイムスタンプ付きの実験用ディレクトリを作成する"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(base_dir, mode, settings_summary, timestamp)
    os.makedirs(path, exist_ok=True)
    return path

def save_json_reports(directory: str, input_data: dict, output_data: dict) -> None:
    """指定されたディレクトリに input.json と output.json を保存する"""
    with open(os.path.join(directory, "input.json"), 'w', encoding='utf-8') as f:
        json.dump(input_data, f, cls=MTWMEncoder, ensure_ascii=False, indent=2)
        
    with open(os.path.join(directory, "output.json"), 'w', encoding='utf-8') as f:
        json.dump(output_data, f, cls=MTWMEncoder, ensure_ascii=False, indent=2)