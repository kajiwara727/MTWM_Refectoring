# runners/dfmm_runner.py
from .base_runner import BaseRunner
from core import apply_auto_factors, build_dfmm_routing_tree, calculate_p_values
from visualization import MixingTreeVisualizer
import os

class DFMMRunner(BaseRunner):
    """
    単一ターゲットごとのDFMMアルゴリズムの結果を可視化するためのランナー
    試薬の注入スケジュール（dispense_inputs）を含めた詳細な木構造を出力
    """
    def run(self):
        print("--- Runner Mode: DFMM (Visualization Only) ---")
        
        # 1. 設定からターゲットを取得し、自動で因数分解（factors）を適用
        targets = apply_auto_factors(
            self.config.TARGETS, 
            self.config.MAX_MIXER_SIZE
        )
        
        # 出力ディレクトリの準備
        output_dir = "output/dfmm_plots"
        os.makedirs(output_dir, exist_ok=True)

        for target in targets:
            print(f"\nターゲット処理中: {target.name}")
            
            # 2. DFMMルーティングツリーの構築
            # skeletonではなくroutingの方を呼ぶことで、試薬割り当て情報を持たせる
            tree_nodes = build_dfmm_routing_tree(target)
            
            # 3. P値の計算（可視化のラベルに使用）
            calculate_p_values(tree_nodes, target.factors)
            
            # 4. 可視化の実行
            print(f"  [Visualizing] グラフ生成を開始...")
            visualizer = MixingTreeVisualizer(tree_nodes)
            
            # ファイル名の決定 (ターゲット名を小文字・アンダースコア化)
            file_name = f"{target.name.replace(' ', '_').lower()}_dfmm.png"
            output_path = os.path.join(output_dir, file_name)
            
            visualizer.draw(
                output_path=output_path, 
                title=f"DFMM Routing Tree: {target.name}",
                show=False
            )
            print(f"  [Saved] -> {output_path}")

        print("\n[Success] すべてのターゲットのDFMM可視化が完了しました。")