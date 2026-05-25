# core/solver/solver_config.py
"""
CP-SAT ソルバーのチューニングパラメータ。

SolverConfig を使って問題規模・手法に合わせたプリセットを選べます。
runners/ から solver インスタンスを生成するときに渡してください。

    solver = MTWMSolver(problem, solver_config=SolverConfig.large_mtwm())
"""

from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# search_branching の整数値 (SatParameters.SearchBranching)
# --------------------------------------------------------------------------
BRANCHING_AUTOMATIC               = 0
BRANCHING_FIXED_SEARCH            = 1
BRANCHING_PORTFOLIO               = 2
BRANCHING_LP_SEARCH               = 3   # LP 誘導: LP 緩和が tight なら最速
BRANCHING_PSEUDO_COST             = 4
BRANCHING_PORTFOLIO_QUICK_RESTART = 6   # 汎用的に良い。デフォルト推奨


@dataclass
class SolverConfig:
    """
    CP-SAT ソルバーのチューニング設定。

    Attributes:
        num_workers (int):
            並列探索のスレッド数。CPUコア数に合わせる。
        max_time_seconds (int):
            求解の上限時間 [秒]。
        linearization_level (int):
            整数積の線形化レベル。
            0=無効, 1=部分的, 2=完全（LP緩和が使えるようになる）。
            **デフォルト 2 推奨**。0 は LP が全く使えず遅い。
        linearize_products (bool):
            True の場合、w*R 積を手動で二値展開し完全線形化する。
            制約は増えるが LP 緩和が tight になり、大規模時に高速化。
        search_branching (int):
            分岐戦略。BRANCHING_* 定数を参照。
            デフォルト PORTFOLIO_QUICK_RESTART(6) は汎用的に良い。
        log_search_progress (bool):
            True の場合、探索の進捗を標準出力に表示する。
        use_dfmm_hints (bool):
            True の場合、DFMM の試薬割り当てを初期解ヒントとして使う。
            実行可能解を早期に見つけやすくなる。
    """

    num_workers: int = 8
    max_time_seconds: int = 5000
    linearization_level: int = 2            # 0 から 2 に変更が最重要
    linearize_products: bool = True          # w*R を二値展開して完全線形化
    search_branching: int = BRANCHING_PORTFOLIO_QUICK_RESTART
    log_search_progress: bool = True
    use_dfmm_hints: bool = True              # DFMM を初期解として提供

    # ------------------------------------------------------------------
    # プリセット
    # ------------------------------------------------------------------

    @classmethod
    def small(cls) -> "SolverConfig":
        """小規模 (S≤18, µ≤2, t≤4): 時間制限を短く"""
        return cls(num_workers=4, max_time_seconds=60, log_search_progress=False)

    @classmethod
    def default_mtwm(cls) -> "SolverConfig":
        """MTWM 標準: 中規模向け"""
        return cls(num_workers=8)

    @classmethod
    def large_mtwm(cls) -> "SolverConfig":
        """MTWM 大規模 (S=135, µ=4, t=6): LP 誘導を強化"""
        return cls(
            num_workers=16,
            max_time_seconds=5000,
            linearize_products=True,
            search_branching=BRANCHING_LP_SEARCH,  # LP が tight なので有効
        )

    @classmethod
    def default_extension(cls) -> "SolverConfig":
        """提案手法（拡張ノード）標準"""
        return cls(num_workers=16, linearize_products=True)

    @classmethod
    def large_extension(cls) -> "SolverConfig":
        """提案手法 大規模: スレッド最大・LP 誘導"""
        return cls(
            num_workers=16,
            max_time_seconds=5000,
            linearize_products=True,
            search_branching=BRANCHING_LP_SEARCH,
        )

    @classmethod
    def fast_feasibility(cls) -> "SolverConfig":
        """実行可能解を最速で得たいとき（解の品質は二の次）"""
        return cls(
            num_workers=16,
            max_time_seconds=300,
            linearize_products=False,
            search_branching=BRANCHING_PORTFOLIO_QUICK_RESTART,
            use_dfmm_hints=True,
        )
