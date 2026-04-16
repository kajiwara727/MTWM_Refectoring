# runners/dfmm_runner.py
from .base_runner import BaseRunner
from core import apply_auto_factors, build_complete_dfmm_tree

class DFMMRunner(BaseRunner):
    """
    単一ターゲットごとのDFMMアルゴリズムの結果データを構築するランナー
    """
    def run(self):
        # self.config.TARGETS -> self.config.targets (設定クラスのプロパティ名に合わせる)
        targets = apply_auto_factors(
            self.config.targets, 
            self.config.max_mixer_size
        )

        tree_structures = {}
        for target_id, target in enumerate(targets):
            # 構築と重み計算がカプセル化された関数を呼ぶ
            tree_nodes = build_complete_dfmm_tree(target, target_id=target_id)
            tree_structures[target.name] = tree_nodes

        # 可視化処理は行わず、main.py 側にデータを返す
        return {"targets": targets, "tree_structures": tree_structures}