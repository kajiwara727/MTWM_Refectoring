from .base_runner import BaseRunner
from core import apply_auto_factors, build_skeleton_tree, calculate_p_values
from core.solver.problem import MTWMProblem

class StandardRunner(BaseRunner):
    """
    MTWM (Multi-Target Waste Minimization) の標準実行モード。
    ターゲットごとの木構造生成、グラフ拡張、最適化ソルバーの実行を一貫して管理します。
    """

    def run(self):
        print("StandardRunner")
        targets = apply_auto_factors(
            self.config.TARGETS, 
            self.config.MAX_MIXER_SIZE
        )
        
        tree_structures = []

        for target in targets:
            print(f"\n--- ターゲット処理開始: {target.name} ---")

            # ① DFMMアルゴリズム: ボトムアップでの木構造（基本グラフ）の構築
            tree_nodes = build_skeleton_tree(target)
            print(f"  [DFMM] 基本の木構造を生成しました (ノード数: {len(tree_nodes)})")
            # ② P値の計算: 各ノードが担当する液滴の重み（濃度寄与度）を計算
            calculate_p_values(tree_nodes, target.factors)
            print("  [DFMM] 各ノードのP値を計算しました")

            tree_structures.append(tree_nodes)

        problem = MTWMProblem(
            targets=targets,
            tree_structures=tree_structures
        )

        print("[Success] MTWMProblemの定式化が完了しました。")
        
        # ==========================================
        # ▼ ここから下を追加して詳細を出力します ▼
        # ==========================================
        print("\n" + "="*50)
        print("🔍 MTWMProblem 内部詳細レポート")
        print("="*50)

        print("\n[1] エッジの接続マップ (どこからどこへ液滴を運べるか)")
        for dst_idx, sources in problem.potential_sources_map.items():
            if sources:
                print(f"  📥 送信先 Node {dst_idx} は以下のノードから受け取り可能:")
                for src in sources:
                    print(f"      <--- 送信元 Node {src}")
            else:
                print(f"  📥 送信先 Node {dst_idx} は外部(試薬)からの注入のみ")

        print("\n[2] ノードごとの変数割り当て詳細 (nodes_metadata)")
        for idx, data in problem.nodes_metadata.items():
            m, l, k = idx
            node_type = "🌱 Leaf (試薬直接注入)" if data['is_leaf'] else "⚙️ Intermediate (中間混合ノード)"
            
            print(f"\n■ Node {idx} [{node_type}]")
            print(f"  ├ P値(濃度寄与度): {data['p_value']}, Factor(分割数): {data['factor']}")
            print(f"  ├ 濃度変数(R)のキー: {data['var_keys_R']}")
            
            if not data['is_leaf']:
                print(f"  ├ 廃棄量変数のキー: {data.get('var_key_waste')}")
            
            print(f"  └ 接続元候補(エッジ)の数: {len(data['potential_src_indices'])} 件")