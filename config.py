# 実行名を定義します。
RUN_NAME = "Test"

# Runnerモード
RUNNER_MODE = "auto"

MAX_MIXER_SIZE = 5
TARGETS = [
    {'name': 'Target 1', 'ratios': [15,1,2]},
    {'name': 'Target 2', 'ratios': [8,1,9]},
    {'name': 'Target 3', 'ratios': [1,8,9]}

    # TimeTest
    # {'name': 'Target 1', 'ratios': [2, 12,3,1]},
    # {'name': 'Target 2', 'ratios': [5,3,4,6]},
    # {'name': 'Target 3', 'ratios': [7,3,7,1]},
    # {'name': 'Target 4', 'ratios': [9,2,6,1]},
    # {'name': 'Target 5', 'ratios': [13,1,1,3]},

]

# --- 'manual' モード用設定 ---
# 'manual' モードでは、'ratios' に加えて 'factors' を明示的に指定する必要があります。
# 'factors' の積は、'ratios' の合計値と一致する必要があります。
# また、'factors' の各要素は MAX_MIXER_SIZE 以下でなければなりません。
TARGETS_FOR_MANUAL_MODE = [
    # 49:98:147_Second
    # {'name': 'Target 1', 'ratios': [23,13,13], 'factors': [7,7]},
    # {'name': 'Target 2', 'ratios': [46,27,25], 'factors': [7,2,7]},
    # {'name': 'Target 3', 'ratios': [69,40,38], 'factors': [7,3,7]},

    # {'name': 'Target 1', 'ratios': [6, 33, 15], 'factors': [3, 3, 3, 2]},
    # {'name': 'Target 1', 'ratios': [2, 3, 7], 'factors': [3, 2, 2]},
    # {'name': 'Target 2', 'ratios': [1, 5, 6], 'factors': [3, 2, 2]},
    # {'name': 'Target 3', 'ratios': [4, 3, 5], 'factors': [3, 2, 2]},
    # {'name': 'Target 3', 'ratios': [4, 5, 9], 'factors': [3, 3, 2]},
    # {'name': 'Target 3', 'ratios': [3, 5, 10], 'factors': [3, 3, 2]},
    # {'name': 'Target 4', 'ratios': [7, 7, 4], 'factors': [3, 3, 2]},
    # {'name': 'Target 2', 'ratios': [60, 25, 5], 'factors': [5, 3, 3, 2]},
    # {'name': 'Target 3', 'ratios': [5, 6, 14], 'factors': [5, 5]},
    # {'name': 'Target 4', 'ratios': [6, 33, 36], 'factors': [3, 5, 5]},
    # {'name': 'Target 1', 'ratios': [102, 26, 3, 3, 122], 'factors': [4, 4, 4, 4]},
    # {"name": "Target 1", "ratios": [2, 11, 5], "factors": [3, 3, 2]},
    # {'name': 'Target 2', 'ratios': [12, 5, 1], 'factors': [3, 3, 2]},
    # {'name': 'Target 3', 'ratios': [5, 6, 14], 'factors': [5, 5]},
    # {'name': 'Target 1', 'ratios': [10, 55, 25], 'factors': [5, 3, 3, 2]},
    # {"name": "Target 2", "ratios": [60, 25, 5], "factors": [5, 3, 3, 2]},
    # {'name': 'Target 3', 'ratios': [15, 18, 42], 'factors': [3, 5, 5]}
]
