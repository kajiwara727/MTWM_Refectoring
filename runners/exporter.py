import json
import os
from datetime import datetime
from dataclasses import is_dataclass, asdict
from core.models import NodeAddress

class MTWMEncoder(json.JSONEncoder):
    """NodeAddressやDataclassを適切にJSON化する"""
    def default(self, o):
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, NodeAddress):
            return f"({o.target_id}, {o.level}, {o.index})"
        return super().default(o)

def export_separated_reports(mode: str, config_summary: str, input_data: dict, output_data: dict) -> tuple[str, str]:
    """
    指定されたモードと設定名に基づいてディレクトリを作成し、入力と出力のJSONを別々に保存する
    構造: output/<mode>/<config_summary>/<timestamp>_input.json (および output.json)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # モードと設定名でフォルダを作成
    target_dir = os.path.join("output", mode, config_summary)
    os.makedirs(target_dir, exist_ok=True)
    
    # タイムスタンプを付与してファイル名を決定
    input_filepath = os.path.join(target_dir, f"{timestamp}_input.json")
    output_filepath = os.path.join(target_dir, f"{timestamp}_output.json")
    
    # 入力ファイルの書き出し
    with open(input_filepath, 'w', encoding='utf-8') as f:
        json.dump(input_data, f, cls=MTWMEncoder, ensure_ascii=False, indent=2)

    # 出力ファイルの書き出し
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, cls=MTWMEncoder, ensure_ascii=False, indent=2)
    
    return input_filepath, output_filepath