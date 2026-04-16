# runners/dfmm_runner.py
from .base_runner import BaseRunner
from core import apply_auto_factors, build_dfmm_routing_tree, calculate_p_values

class DFMMRunner(BaseRunner):
    """
    単一ターゲットごとのDFMMアルゴリズムの結果を可視化するためのランナー
    """
    def run(self):
        print("--- Runner Mode: DFMM (Visualization Only) ---")
        
        targets = apply_auto_factors(
            self.config.TARGETS, 
            self.config.MAX_MIXER_SIZE
        )

        for target in targets:
            print(f"\nターゲット処理中: {target.name}")
            
            tree_nodes = build_dfmm_routing_tree(target)
            calculate_p_values(tree_nodes, target.factors)
            
            # BaseRunnerの共通メソッドを呼び出す
            file_name = f"{target.name.replace(' ', '_').lower()}_dfmm.png"
            self.visualize(
                mode='dfmm',
                data=tree_nodes,
                output_filename=file_name,
                title=f"DFMM Routing Tree: {target.name}"
            )

        print("\n[Success] すべてのターゲットのDFMM可視化が完了しました。")