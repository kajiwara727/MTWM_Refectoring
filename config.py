from dataclasses import dataclass, field
from typing import List, Optional
from core.models import Target

@dataclass
class RandomConfig:
    num_targets: int
    num_reagents: int
    ratio_sum: int
    num_executions: int = 1
    visualize: bool = True

@dataclass
class MTWMConfig:
    runner_mode: str
    max_mixer_size: int
    targets: List[Target] = field(default_factory=list)
    random_config: Optional[RandomConfig] = None
    base_output_dir: str = "output"  # 追加: 出力先のベースディレクトリ
    visualize_enabled: bool = True   # 追加: 全体の可視化フラグ

    def __post_init__(self):
        valid_modes = ["auto", "dfmm", "random", "proposed"]
        if self.runner_mode not in valid_modes:
            raise ValueError(f"runner_mode は {valid_modes} のいずれかである必要があります。")
        
        if self.max_mixer_size <= 1:
            raise ValueError("max_mixer_size は2以上を指定してください。")
            
        if self.runner_mode == "random":
            if not self.random_config:
                raise ValueError("random モードでは random_config の指定が必須です。")

def get_default_config() -> MTWMConfig:
    return MTWMConfig(
        runner_mode="auto",
        max_mixer_size=5,
        targets=[
            Target(name='Target 1', ratios=[31,13,17,34,1,21,18]),
            Target(name='Target 2', ratios=[9,9,14,34,19,30,20]),
            Target(name='Target 3', ratios=[14,9,24,45,10,28,5]),
            Target(name='Target 4', ratios=[22,21,11,23,16,22,20])
        ],
        random_config=RandomConfig(
            num_targets=3,
            num_reagents=3,
            ratio_sum=20
        )
    )