# config.py
"""
アプリケーション設定。

runner_mode でアルゴリズムを選択できます:
  "auto"      : MTWM（スケルトンツリー + CP-SAT 最適化）
  "dfmm"      : 純粋 DFMM（ヒューリスティックのみ、最適化なし）
  "random"    : ランダム実験（ランダムターゲットを多数試行）
  "proposed"  : 試作提案手法（最多試薬フィルタリングで探索空間削減）
  "extension" : 【提案手法・論文採用】拡張ノード導入による廃棄液削減

推奨:
  - MTWM との比較実験  → "auto" と "extension" を使い分け
  - 大規模インスタンス → "auto" を基準に "extension" を試す
    （拡張ノードが増えると計算時間が増大する場合あり）
"""

from dataclasses import dataclass, field
from typing import List, Optional
from core.models import Target


@dataclass
class RandomConfig:
    num_targets: int
    num_reagents: int
    ratio_sum: int
    num_executions: int = 20
    visualize: bool = True


@dataclass
class MTWMConfig:
    """
    アプリケーション全体の設定。

    Attributes:
        runner_mode (str):
            使用するアルゴリズム。
            "auto" | "dfmm" | "random" | "proposed" | "extension"
        max_mixer_size (int):
            最大ミキサーサイズ M（2 以上）。
            拡張ノードは weight > M のノードが対象となるため、
            この値がアルゴリズムの動作に大きく影響する。
        targets (List[Target]):
            最適化対象のターゲット液滴リスト。
        random_config (Optional[RandomConfig]):
            runner_mode == "random" の場合に必須。
        base_output_dir (str):
            出力ディレクトリのベースパス。
        visualize_enabled (bool):
            可視化（PNG 出力）を行うかどうか。
    """
    runner_mode: str
    max_mixer_size: int
    targets: List[Target] = field(default_factory=list)
    random_config: Optional[RandomConfig] = None
    base_output_dir: str = "output"
    visualize_enabled: bool = True

    def __post_init__(self):
        valid_modes = ["auto", "dfmm", "random", "proposed", "extension", "compare"]
        if self.runner_mode not in valid_modes:
            raise ValueError(
                f"runner_mode は {valid_modes} のいずれかである必要があります。"
                f"  指定値: '{self.runner_mode}'"
            )

        if self.max_mixer_size <= 1:
            raise ValueError("max_mixer_size は 2 以上を指定してください。")

        if self.runner_mode == "random" and not self.random_config:
            raise ValueError("random モードでは random_config の指定が必須です。")

        if self.runner_mode == "compare" and not self.targets and not self.random_config:
            raise ValueError(
                "compare モードでは targets または random_config のいずれかが必要です。"
            )


# ------------------------------------------------------------------
# デフォルト設定
# ------------------------------------------------------------------

def get_default_config() -> MTWMConfig:
    """
    デフォルト設定を返す。

    runner_mode を変更するだけで比較実験が可能:
      - "auto"      : MTWM（ベースライン）
      - "extension" : 提案手法（拡張ノード）
    """
    return MTWMConfig(
        runner_mode="extension",   # ← ここを "extension" に変える
        max_mixer_size=5,
        targets=[
            Target(name='Target 1', ratios=[15, 1, 2]),
            Target(name='Target 2', ratios=[8,  1, 9]),
            Target(name='Target 3', ratios=[1,  8, 9]),
        ],
        random_config=RandomConfig(
            num_targets=3,
            num_reagents=3,
            ratio_sum=20,
        ),
    )


def get_paper_example_config() -> MTWMConfig:
    """
    論文 Fig.5・Fig.6 の例題設定:
        targets: 15:1:2, 8:1:9, 1:8:9  /  M = 5
    拡張ノードとMTWMの比較に使用。
    """
    return MTWMConfig(
        runner_mode="extension",
        max_mixer_size=5,
        targets=[
            Target(name='Target 1', ratios=[15, 1, 2]),
            Target(name='Target 2', ratios=[8,  1, 9]),
            Target(name='Target 3', ratios=[1,  8, 9]),
        ],
    )
