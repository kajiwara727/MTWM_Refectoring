from dataclasses import dataclass
from typing import List
from core import Target

@dataclass
class MTWMConfig:
    runner_mode: str
    max_mixer_size: int
    targets: List[Target]

def get_default_config() -> MTWMConfig:
    return MTWMConfig(
        runner_mode="dfmm",
        max_mixer_size=5,
        targets=[
            Target(name='Target 1', ratios=[12,5,1]),
            Target(name='Target 2', ratios=[2,3,13]),
            Target(name='Target 3', ratios=[1, 8, 9])
        ]
    )