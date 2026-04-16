import math
import time
from ortools.sat.python import cp_model
from core.solver.problem import MTWMProblem

class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """解が見つかるたびに進捗を表示するコールバック"""
    def __init__(self):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.solution_count = 0
        self.start_time = time.time()

    def on_solution_callback(self):
        self.solution_count += 1
        current_time = time.time()
        print(f"Solution #{self.solution_count}: Objective = {self.ObjectiveValue()}, Time = {current_time - self.start_time:.2f}s")


class MTWMSolver:
    """
    MTWMProblem を Or-Tools CP-SAT モデルに変換し、最適化を実行するクラス。
    タプルベースのインデックス (m, l, k) を使用して変数をフラットに管理します。
    """
    def __init__(self, problem: MTWMProblem, objective_mode="waste_fluids"):
        self.problem = problem
        self.objective_mode = objective_mode
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # フラットな変数管理辞書
        self.node_vars = {}  # (m, l, k) -> 変数の辞書
        self.edge_vars = {}  # (src_idx, dst_idx) -> 共有量の変数

        self._configure_solver()
        self._build_model()

    def _configure_solver(self):
        self.solver.parameters.num_workers = 0  # 0で自動的に全コア使用
        self.solver.parameters.max_time_in_seconds = 300.0 # ひとまず5分でタイムアウト
        self.solver.parameters.log_search_progress = True

    def _build_model(self):
        """モデルの変数と制約を構築"""
        self._define_variables()
        self._set_initial_target_constraints()
        self._set_mass_conservation_constraints()
        self._set_concentration_constraints()
        self._set_mixer_capacity_and_activity_constraints()
        self._set_objective_function()

    def _define_variables(self):
        """nodes_metadataとpotential_sources_mapから全変数を一括生成"""
        
        # 1. ノード内の変数生成
        for idx, meta in self.problem.nodes_metadata.items():
            m, l, k = idx
            f_val = meta['factor']
            p_val = meta['p_value']
            
            vars_dict = {
                'R': [self.model.NewIntVar(0, p_val, f"R_{m}_{l}_{k}_t{t}") for t in range(self.problem.num_reagents)],
                'r': [self.model.NewIntVar(0, max(0, f_val - 1), f"r_{m}_{l}_{k}_t{t}") for t in range(self.problem.num_reagents)],
                'total_input': self.model.NewIntVar(0, f_val, f"total_{m}_{l}_{k}"),
                'is_active': self.model.NewBoolVar(f"isActive_{m}_{l}_{k}")
            }
            
            # リーフノード以外は waste fluids 変数を持つ
            if not meta['is_leaf']:
                vars_dict['waste_fluids'] = self.model.NewIntVar(0, f_val, f"waste_{m}_{l}_{k}")
                
            self.node_vars[idx] = vars_dict

        # 2. 共有（エッジ）変数の生成
        for dst_idx, src_indices in self.problem.potential_sources_map.items():
            for src_idx in src_indices:
                limit = self.problem.nodes_metadata[src_idx]['factor']
                name = f"edge_{src_idx[0]}_{src_idx[1]}_{src_idx[2]}_to_{dst_idx[0]}_{dst_idx[1]}_{dst_idx[2]}"
                self.edge_vars[(src_idx, dst_idx)] = self.model.NewIntVar(0, limit, name)

    def _set_initial_target_constraints(self):
        """ルートノード (l=0) の濃度比率をTargetの比率に固定"""
        for m, target in enumerate(self.problem.targets):
            for idx, meta in self.problem.nodes_metadata.items():
                if idx[0] == m and idx[1] == 0:  # 各ターゲットのルート
                    for t in range(self.problem.num_reagents):
                        self.model.Add(self.node_vars[idx]['R'][t] == target.ratios[t])

    def _set_mass_conservation_constraints(self):
        """質量保存則: 合計入力 = 試薬の和 + 受信した共有液滴の和"""
        for dst_idx, meta in self.problem.nodes_metadata.items():
            inputs = list(self.node_vars[dst_idx]['r']) # 試薬
            
            # dst_idx に入ってくるエッジをすべて取得
            for src_idx in self.problem.potential_sources_map.get(dst_idx, []):
                inputs.append(self.edge_vars[(src_idx, dst_idx)])
                
            self.model.Add(self.node_vars[dst_idx]['total_input'] == sum(inputs))

    def _set_concentration_constraints(self):
        """LCMを用いた濃度保存則。文字列解析を廃止しタプルで計算"""
        for dst_idx, meta_dst in self.problem.nodes_metadata.items():
            p_dst = meta_dst['p_value']
            f_dst = meta_dst['factor']
            
            src_indices = self.problem.potential_sources_map.get(dst_idx, [])
            if not src_indices and meta_dst['is_leaf']:
                # リーフノードは濃度(R) = 試薬注入量(r)
                for t in range(self.problem.num_reagents):
                    self.model.Add(self.node_vars[dst_idx]['R'][t] == self.node_vars[dst_idx]['r'][t])
                continue

            # LCMの計算 (math.lcm は複数の引数を取れる)
            p_values = [self.problem.nodes_metadata[s]['p_value'] for s in src_indices] + [p_dst]
            common_lcm = math.lcm(*p_values)
            
            for t in range(self.problem.num_reagents):
                # 左辺: Output
                lhs_scale = common_lcm // p_dst
                lhs_term = f_dst * self.node_vars[dst_idx]['R'][t] * lhs_scale
                
                # 右辺: Inputs (純粋試薬 + 共有)
                rhs_terms = []
                # 1. 試薬 (P=1とみなすのでスケールはLCMそのまま)
                rhs_terms.append(self.node_vars[dst_idx]['r'][t] * common_lcm)
                
                # 2. 共有液滴
                for src_idx in src_indices:
                    scale = common_lcm // self.problem.nodes_metadata[src_idx]['p_value']
                    w_var = self.edge_vars[(src_idx, dst_idx)]
                    R_src = self.node_vars[src_idx]['R'][t]
                    
                    # Or-Toolsの乗算制約用の中間変数
                    max_prod = self.problem.nodes_metadata[src_idx]['factor'] * self.problem.nodes_metadata[src_idx]['p_value']
                    prod_var = self.model.NewIntVar(0, max_prod, f"prod_{src_idx}_to_{dst_idx}_t{t}")
                    self.model.AddMultiplicationEquality(prod_var, [w_var, R_src])
                    
                    rhs_terms.append(prod_var * scale)
                    
                self.model.Add(lhs_term == sum(rhs_terms))

    def _set_mixer_capacity_and_activity_constraints(self):
        """ミキサーの容量とアクティビティ制約、および waste fluids の計算"""
        for idx, meta in self.problem.nodes_metadata.items():
            l = idx[1]
            f_val = meta['factor']
            total_input = self.node_vars[idx]['total_input']
            is_active = self.node_vars[idx]['is_active']
            
            # アクティブなら total_input == factor、非アクティブなら 0
            if l == 0:
                self.model.Add(total_input == f_val)
                self.model.Add(is_active == 1)
            else:
                self.model.Add(total_input == f_val * is_active)
                
            # 出力液滴と waste fluids の計算
            if not meta['is_leaf']:
                # このノードから出ていく全エッジを取得
                outgoing_edges = [
                    self.edge_vars[(src, dst)] 
                    for (src, dst) in self.edge_vars if src == idx
                ]
                total_used = sum(outgoing_edges) if outgoing_edges else 0
                
                # アクティブ時のみ、最低1つはどこかに送信する
                if outgoing_edges:
                    self.model.Add(total_used >= 1).OnlyEnforceIf(is_active)
                    self.model.Add(total_used == 0).OnlyEnforceIf(is_active.Not())
                
                # waste fluids = 生産量 - 使用量
                waste_var = self.node_vars[idx]['waste_fluids']
                self.model.Add(waste_var == total_input - total_used)

    def _set_objective_function(self):
        if self.objective_mode == "waste_fluids":
            all_waste_vars = [
                v['waste_fluids'] for meta, v in zip(self.problem.nodes_metadata.values(), self.node_vars.values()) 
                if 'waste_fluids' in v
            ]
            self.model.Minimize(sum(all_waste_vars))

    def solve(self):
        print(f"\n--- Solving MTWM ({self.objective_mode}) ---")
        start_time = time.time()
        printer = SolutionPrinter()
        
        status = self.solver.Solve(self.model, printer)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
            print(f"Status: {status_str}, Objective (waste fluids): {int(self.solver.ObjectiveValue())}")
            print(f"Time: {time.time() - start_time:.2f}s")
            return self._extract_solution()
        else:
            print("No solution found.")
            return None

    def _extract_solution(self):
        """解をPythonの辞書形式で抽出 (エッジ情報を追加)"""
        result = {
            "objective_value": int(self.solver.ObjectiveValue()),
            "total_waste_fluids": 0,
            "nodes": [],
            "edges": [] # 🌟 新規追加: 実際に使用された共有接続（流量）
        }
        
        # 1. アクティブなノードの抽出（変更なし）
        for idx, vars_dict in self.node_vars.items():
            if self.solver.Value(vars_dict['is_active']):
                node_res = {
                    "id": idx,
                    "total_input": self.solver.Value(vars_dict['total_input']),
                    "R": [self.solver.Value(v) for v in vars_dict['R']],
                    "r": [self.solver.Value(v) for v in vars_dict['r']],
                }
                if 'waste_fluids' in vars_dict:
                    waste = self.solver.Value(vars_dict['waste_fluids'])
                    node_res['waste_fluids'] = waste
                    result["total_waste_fluids"] += waste
                result["nodes"].append(node_res)
                
        # 2. 🌟 新規追加: 流量が1以上のエッジ（接続）を抽出
        for (src_idx, dst_idx), var in self.edge_vars.items():
            vol = self.solver.Value(var)
            if vol > 0:
                result["edges"].append({
                    "source": src_idx,
                    "target": dst_idx,
                    "volume": vol
                })
                
        return result