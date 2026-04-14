from typing import List, Dict, Any

# 合計値を上限値以下の掛け算に分解
def find_factors_for_sum(target_sum: int, max_factor: int) -> List[int]:
    """
    target_sum を max_factor 以下の整数の積に分解する。

    Returns:
        List[int]: 因数のリスト（降順）
    """
    
    # 1以下は分解対象外
    if target_sum <= 1:
        return []

    current_value = target_sum
    factors = []

    # 値が1になるまで（完全に分解し切るまで）ループを続ける
    while current_value > 1:
        found_divisor = False

        # max_factor から 2 に向かって、割り切れる最大の数を探す
        for candidate_factor in range(max_factor, 1, -1):
            if current_value % candidate_factor == 0:
                factors.append(candidate_factor)
                current_value //= candidate_factor  # 商で更新
                found_divisor = True
                break  # 割り切れたら現在のループを抜け、再び最大値から探す

        if not found_divisor:
            raise ValueError(
                f"{target_sum} は max_factor={max_factor} 以下では分解できません"
            )

    # 結果を大きい順（降順）にソートして返す
    return sorted(factors, reverse=True)

def apply_auto_factors(
    targets_config: List[Dict[str, Any]],
    max_mixer_size: int
) -> List[Dict[str, Any]]:
    """
    各ターゲットに対して因数分解を行い、'factors' を追加

    Args:
        targets_config: ターゲット設定のリスト
        max_mixer_size: 使用可能な最大ミキサーサイズ

    Returns:
        因数情報を追加した targets_config
    """

    for target in targets_config:
        total_ratio = sum(target["ratios"])
        target_name = target.get("name", "Unknown")

        try:
            factors = find_factors_for_sum(total_ratio, max_mixer_size)
        except ValueError:
            raise ValueError(
                f"ターゲット '{target_name}' の因数分解に失敗しました "
                f"(max_mixer_size={max_mixer_size})"
            )

        target["factors"] = factors

    return targets_config