# core/io/targets_io.py
"""
ターゲット設定の保存・読み込みユーティリティ。

比較実験の再現性のために、ランダム生成したターゲットを JSON で保存し、
後から同じターゲットで別の手法を実行できるようにする。

保存形式 (targets.json):
    {
        "max_mixer_size": 5,
        "source": "random",
        "created_at": "2026-05-25T17:34:59.123456",
        "num_targets": 3,
        "num_reagents": 3,
        "targets": [
            {"name": "Target_1", "ratios": [3, 5, 2]},
            ...
        ]
    }

使い方:
    # 保存
    save_targets(targets, max_mixer_size=5, file_path="session/targets.json", source="random")

    # 読み込み
    targets, max_mixer_size, meta = load_targets("session/targets.json")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.models import Target


def save_targets(
    targets: List[Target],
    max_mixer_size: int,
    file_path: str,
    source: str = "manual",
    extra_meta: Dict[str, Any] = None,
) -> str:
    """
    ターゲット設定を JSON ファイルに保存する。

    apply_auto_factors 適用前の raw ターゲットを保存することを推奨。
    ロード時に prepare_targets() が再適用されるため、再現性が保たれる。

    Args:
        targets:        保存する Target リスト
        max_mixer_size: 最大ミキサーサイズ
        file_path:      保存先ファイルパス（親ディレクトリは自動作成）
        source:         生成元の識別子 ("random" | "manual" | "paper_example" | "compare")
        extra_meta:     追加メタ情報（任意キーワード引数として JSON に追記）

    Returns:
        保存したファイルの絶対パス文字列
    """
    data: Dict[str, Any] = {
        "max_mixer_size": max_mixer_size,
        "source": source,
        "created_at": datetime.now().isoformat(),
        "num_targets": len(targets),
        "num_reagents": len(targets[0].ratios) if targets else 0,
        "targets": [
            {"name": t.name, "ratios": list(t.ratios)}
            for t in targets
        ],
    }
    if extra_meta:
        data.update(extra_meta)

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path.resolve())


def load_targets(file_path: str) -> Tuple[List[Target], int, Dict[str, Any]]:
    """
    JSON ファイルからターゲット設定を読み込む。

    Args:
        file_path: 読み込む targets.json のパス

    Returns:
        (targets, max_mixer_size, meta_dict)
          - targets:        Target のリスト（apply_auto_factors 前の raw）
          - max_mixer_size: 保存時の max_mixer_size
          - meta_dict:      JSON 全フィールド（source, created_at 等の参照用）

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        ValueError:        "targets" フィールドがない場合
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"targets ファイルが見つかりません: {file_path}")

    data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    if "targets" not in data:
        raise ValueError(f'"targets" フィールドがありません: {file_path}')

    targets = [
        Target(name=t["name"], ratios=t["ratios"])
        for t in data["targets"]
    ]
    max_mixer_size = int(data.get("max_mixer_size", 5))

    return targets, max_mixer_size, data
