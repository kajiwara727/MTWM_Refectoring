# core/solver/extension_solver.py
"""
【提案手法】拡張ノードを組み込んだ CP-SAT ソルバー（論文 Section III-C）

MTWMSolver を継承し、以下の変数・制約を追加:
  変数:
    C^k_{p,h}       (ext_node_vars)    : 拡張ノードの試薬比率
    is_active_{p,h} (ext_node_vars)    : 拡張ノードのアクティブフラグ
    waste_{p,h}     (ext_node_vars)    : 拡張ノードの廃棄液滴量
    z^{m,l,i}_{p,h} (ext_edge_vars)   : 拡張ノード → 通常ノードのフロー量 (BoolVar)

  追加・更新制約:
    eq.10: 濃度計算に z 項を追加
    eq.11: フロー保存則に z 項を追加
    eq.12: 2 * C^k = R1^k + R2^k（拡張ノードの濃度決定）
    eq.13: 0 ≤ z ≤ 1  (BoolVar)
    + 廃棄: waste_{p,h} = 2 * is_active - sum(z)
    + 通常ノードの total_used に拡張ノードへの供給を加算

チューニングの要点:
  - z を BoolVar にすることで OnlyEnforceIf による z*C の完全線形化が可能
  - SolverConfig.default_extension() のデフォルトで 16 workers / linearize_products=True
  - DFMM ヒントを有効化（継承した _add_dfmm_hints を利用）
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from core.models import NodeAddress, ExtensionNodeAddress
from core.solver.solver import MTWMSolver, NodeVariables, SolutionPrinter
from core.solver.solver_config import SolverConfig
from core.solver.extension_problem import ExtensionMTWMProblem
from core.solver.dto import (
    OptimizationResult, NodeFlowResult, EdgeFlowResult,
    ExtensionNodeFlowResult,
)


@dataclass
class ExtensionNodeVariables:
    """拡張ノード u_{p,h} の CP-SAT 変数群"""
    C: List[cp_model.IntVar] = field(default_factory=list)  # C^k_{p,h}
    is_active: Optional[cp_model.IntVar] = None             # アクティブフラグ
    waste_fluids: Optional[cp_model.IntVar] = None          # 廃棄液滴量


class ExtensionMTWMSolver(MTWMSolver):
    """
    拡張ノードを組み込んだ提案手法のソルバー。

    Python の MRO（メソッド解決順序）を利用し、
    super().__init__() 呼び出し時に _build_model() がオーバーライド版に
    解決されることで、親クラスのモデル構築に割り込む。

    Args:
        problem:       ExtensionMTWMProblem インスタンス
        objective_mode: "waste_fluids" のみサポート
        solver_config: SolverConfig。省略時は SolverConfig.default_extension()
                       (16 workers, linearize_products=True) が使われる。
    """

    def __init__(
        self,
        problem: ExtensionMTWMProblem,
        objective_mode: str = "waste_fluids",
        solver_config: Optional[SolverConfig] = None,
    ):
        # _build_model() が super().__init__() 内で呼ばれるより前に辞書を初期化
        self.ext_node_vars: Dict[ExtensionNodeAddress, ExtensionNodeVariables] = {}
        self.ext_edge_vars: Dict[Tuple[ExtensionNodeAddress, NodeAddress], cp_model.IntVar] = {}

        # デフォルトは拡張手法向けプリセット（16 workers, linearize_products=True）
        cfg = solver_config or SolverConfig.default_extension()
        super().__init__(problem, objective_mode, solver_config=cfg)

    # ------------------------------------------------------------------
    # モデル構築
    # ------------------------------------------------------------------

    def _build_model(self) -> None:
        """拡張ノード用ステップを追加したモデル構築"""
        self._define_variables()
        self._define_extension_variables()           # ★ 拡張ノード変数

        self._set_initial_target_constraints()
        self._set_mass_conservation_constraints()    # ★ z 項を含む更新版
        self._set_concentration_constraints()        # ★ z, C 項を含む更新版
        self._set_mixer_capacity_and_activity_constraints()  # ★ 拡張入力消費を追加
        self._set_extension_node_constraints()       # ★ 拡張ノード固有の制約

        self._set_objective_function()               # ★ 拡張ノードの廃棄も含む
        self._set_ratio_sum_constraints()

    def _define_extension_variables(self) -> None:
        """
        拡張ノードの変数を定義する。
          C^k_{p,h} ∈ [0, p]
          is_active_{p,h} ∈ {0, 1}   (BoolVar)
          waste_{p,h} ∈ [0, 2]
          z^{m,l,i}_{p,h} ∈ {0, 1}  (BoolVar: z は 0 か 1 なので BoolVar が最適)
        """
        for ext_node in self.problem.extension_nodes:
            ext_addr = ext_node.address
            p = ext_addr.weight

            C_vars = [
                self.model.NewIntVar(0, p, f"C_{p}_{ext_addr.index}_t{t}")
                for t in range(self.problem.num_reagents)
            ]
            is_active = self.model.NewBoolVar(f"ext_active_{p}_{ext_addr.index}")
            waste = self.model.NewIntVar(0, 2, f"ext_waste_{p}_{ext_addr.index}")

            self.ext_node_vars[ext_addr] = ExtensionNodeVariables(
                C=C_vars, is_active=is_active, waste_fluids=waste
            )

        # フロー変数 z^{m,l,i}_{p,h} ∈ {0, 1}
        # z は 0 か 1 しか取れないため BoolVar として宣言 → LP 緩和が自動的に tight
        for dst_addr, ext_addrs in self.problem.extension_sources_map.items():
            for ext_addr in ext_addrs:
                name = (
                    f"z_ext_{ext_addr.weight}_{ext_addr.index}"
                    f"_to_{dst_addr.target_id}_{dst_addr.level}_{dst_addr.index}"
                )
                self.ext_edge_vars[(ext_addr, dst_addr)] = self.model.NewBoolVar(name)

    # ------------------------------------------------------------------
    # 制約: フロー保存則（式 11）
    # ------------------------------------------------------------------

    def _set_mass_conservation_constraints(self) -> None:
        """
        フロー保存則（eq.11）:
          sum(r) + sum(w) + sum(z) = total_input
        """
        for dst_addr in self.problem.nodes_metadata:
            inputs = list(self.node_vars[dst_addr].r)

            # 通常ノードからのエッジ（w）
            for src_addr in self.problem.potential_sources_map.get(dst_addr, []):
                inputs.append(self.edge_vars[(src_addr, dst_addr)])

            # 拡張ノードからのエッジ（z: BoolVar）
            for ext_addr in self.problem.extension_sources_map.get(dst_addr, []):
                inputs.append(self.ext_edge_vars[(ext_addr, dst_addr)])

            self.model.Add(self.node_vars[dst_addr].total_input == sum(inputs))

    # ------------------------------------------------------------------
    # 制約: 濃度整合性（式 10）
    # ------------------------------------------------------------------

    def _set_concentration_constraints(self) -> None:
        """
        濃度整合性制約（eq.10）:
          f_dst * R^k_dst * scale = P_dst * r^k + sum_w[...] + sum_z[...]

        チューニング:
          - w*R 積: solver_cfg.linearize_products=True なら _add_linear_product() で線形化
          - z*C 積: z が BoolVar なので OnlyEnforceIf で完全線形化（AddMultiplicationEquality 不要）
        """
        use_lin = self.solver_cfg.linearize_products

        for dst_addr, meta_dst in self.problem.nodes_metadata.items():
            p_dst = meta_dst.droplet_weight
            f_dst = meta_dst.factor

            src_addresses = self.problem.potential_sources_map.get(dst_addr, [])
            ext_addresses = self.problem.extension_sources_map.get(dst_addr, [])

            # リーフノードで接続が一切ない場合: R == r（直接注入のみ）
            if not src_addresses and not ext_addresses and meta_dst.is_leaf:
                for t in range(self.problem.num_reagents):
                    self.model.Add(
                        self.node_vars[dst_addr].R[t] == self.node_vars[dst_addr].r[t]
                    )
                continue

            # LCM を計算（通常ノード重み + 拡張ノード重み + 宛先ノード重み）
            all_p = (
                [self.problem.nodes_metadata[s].droplet_weight for s in src_addresses]
                + [ea.weight for ea in ext_addresses]
                + [p_dst]
            )
            common_lcm = math.lcm(*all_p)

            for t in range(self.problem.num_reagents):
                lhs_scale = common_lcm // p_dst
                lhs_term = f_dst * self.node_vars[dst_addr].R[t] * lhs_scale

                rhs_terms = [self.node_vars[dst_addr].r[t] * common_lcm]

                # 通常ノードからの項（w * R_src）
                # w_max >= 2 の場合は二値展開で完全線形化
                for src_addr in src_addresses:
                    meta_src = self.problem.nodes_metadata[src_addr]
                    scale  = common_lcm // meta_src.droplet_weight
                    w_var  = self.edge_vars[(src_addr, dst_addr)]
                    R_src  = self.node_vars[src_addr].R[t]
                    w_max  = meta_src.factor
                    R_max  = meta_src.droplet_weight

                    name_pfx = (
                        f"prod_{src_addr.target_id}_{src_addr.level}_{src_addr.index}"
                        f"_to_{dst_addr.target_id}_{dst_addr.level}_{dst_addr.index}_t{t}"
                    )
                    prod_var = self.model.NewIntVar(0, w_max * R_max, name_pfx)

                    if use_lin:
                        self._add_linear_product(prod_var, w_var, w_max, R_src, R_max, name_pfx)
                    else:
                        self.model.AddMultiplicationEquality(prod_var, [w_var, R_src])

                    rhs_terms.append(prod_var * scale)

                # 拡張ノードからの項（z * C^k_{p,h}）
                # z は BoolVar なので OnlyEnforceIf で完全線形化（LP 緩和が tight）
                for ext_addr in ext_addresses:
                    p_ext  = ext_addr.weight
                    scale  = common_lcm // p_ext
                    z_var  = self.ext_edge_vars[(ext_addr, dst_addr)]   # BoolVar
                    C_var  = self.ext_node_vars[ext_addr].C[t]

                    # prod = z * C（z ∈ {0,1} → OnlyEnforceIf で線形化）
                    prod_var = self.model.NewIntVar(
                        0, p_ext,
                        f"prod_ext_{p_ext}_{ext_addr.index}"
                        f"_to_{dst_addr.target_id}_{dst_addr.level}_{dst_addr.index}_t{t}"
                    )
                    self.model.Add(prod_var == 0).OnlyEnforceIf(z_var.Not())
                    self.model.Add(prod_var == C_var).OnlyEnforceIf(z_var)

                    rhs_terms.append(prod_var * scale)

                self.model.Add(lhs_term == sum(rhs_terms))

    # ------------------------------------------------------------------
    # 制約: ミキサー容量・アクティビティ（廃棄 + 拡張ノード消費を含む）
    # ------------------------------------------------------------------

    def _set_mixer_capacity_and_activity_constraints(self) -> None:
        """
        通常ノードの廃棄計算に、拡張ノードへの供給（1単位ずつ）を加算する。

        廃棄 = total_input - sum(w 出力) - sum(拡張ノードへの供給)
        """
        for addr, meta in self.problem.nodes_metadata.items():
            f_val = meta.factor
            vars_obj = self.node_vars[addr]

            if addr.level == 0:
                self.model.Add(vars_obj.total_input == f_val)
                self.model.Add(vars_obj.is_active == 1)
            else:
                self.model.Add(vars_obj.total_input == f_val * vars_obj.is_active)

            if not meta.is_leaf:
                # 通常のアウトゴーイングエッジ
                outgoing_w = [
                    var for (src, dst), var in self.edge_vars.items() if src == addr
                ]

                # このノードを入力とする拡張ノードへの供給（1単位ずつ）
                # is_active は BoolVar なのでそのまま加算可能
                ext_consumptions = [
                    self.ext_node_vars[ext_addr].is_active
                    for ext_addr in self.problem.extension_input_map.get(addr, [])
                ]

                all_outgoing = outgoing_w + ext_consumptions
                total_used = sum(all_outgoing) if all_outgoing else 0

                if all_outgoing:
                    self.model.Add(total_used >= 1).OnlyEnforceIf(vars_obj.is_active)
                    self.model.Add(total_used == 0).OnlyEnforceIf(vars_obj.is_active.Not())

                self.model.Add(vars_obj.waste_fluids == vars_obj.total_input - total_used)

    # ------------------------------------------------------------------
    # 制約: 拡張ノード固有
    # ------------------------------------------------------------------

    def _set_extension_node_constraints(self) -> None:
        """
        拡張ノード u_{p,h} の制約:
          - eq.12: 2 * C^k = R1^k + R2^k （アクティブ時のみ）
          - アクティブ ↔ 出力あり（sum(z) >= 1）
          - 総出力 sum(z) ≤ f_{p,h} = 2
          - 廃棄: waste = 2 * is_active - sum(z)
          - 入力ノードの両方がアクティブのときのみ拡張ノードをアクティブにできる
        """
        for ext_node in self.problem.extension_nodes:
            ext_addr = ext_node.address
            p = ext_addr.weight
            in1_addr = ext_node.input_1
            in2_addr = ext_node.input_2

            ext_vars = self.ext_node_vars[ext_addr]
            R1_vars = self.node_vars[in1_addr].R
            R2_vars = self.node_vars[in2_addr].R
            in1_active = self.node_vars[in1_addr].is_active
            in2_active = self.node_vars[in2_addr].is_active

            # この拡張ノードから全宛先へのフロー変数（BoolVar）
            outgoing_z = [
                var for (ea, _da), var in self.ext_edge_vars.items() if ea == ext_addr
            ]

            # ---- アクティビティ制約 ----
            if outgoing_z:
                total_z = sum(outgoing_z)
                # アクティブ ⟺ 何らかの出力がある
                self.model.Add(total_z >= 1).OnlyEnforceIf(ext_vars.is_active)
                self.model.Add(total_z == 0).OnlyEnforceIf(ext_vars.is_active.Not())
                # 総出力 ≤ f_{p,h} = 2
                self.model.Add(total_z <= 2 * ext_vars.is_active)
            else:
                # 有効な出力先がなければ非アクティブ
                self.model.Add(ext_vars.is_active == 0)

            # ---- 入力ノードが両方アクティブのときのみ拡張ノードをアクティブにできる ----
            self.model.AddImplication(ext_vars.is_active, in1_active)
            self.model.AddImplication(ext_vars.is_active, in2_active)

            # ---- 濃度制約 eq.12: 2 * C^k = R1^k + R2^k ----
            for t in range(self.problem.num_reagents):
                C_var = ext_vars.C[t]
                # アクティブ時: 2 * C == R1 + R2
                self.model.Add(
                    2 * C_var == R1_vars[t] + R2_vars[t]
                ).OnlyEnforceIf(ext_vars.is_active)
                # 非アクティブ時: C == 0
                self.model.Add(C_var == 0).OnlyEnforceIf(ext_vars.is_active.Not())

            # ---- 比率の合計: sum(C^k) = p * is_active ----
            self.model.Add(sum(ext_vars.C) == p * ext_vars.is_active)

            # ---- 廃棄: waste = 2 * is_active - sum(z) ----
            total_z_for_waste = sum(outgoing_z) if outgoing_z else 0
            self.model.Add(
                ext_vars.waste_fluids == 2 * ext_vars.is_active - total_z_for_waste
            )

    # ------------------------------------------------------------------
    # 目的関数（拡張ノードの廃棄を含む）
    # ------------------------------------------------------------------

    def _set_objective_function(self) -> None:
        if self.objective_mode == "waste_fluids":
            # 通常ノードの廃棄
            regular_waste = [
                v.waste_fluids for v in self.node_vars.values()
                if v.waste_fluids is not None
            ]
            # 拡張ノードの廃棄
            ext_waste = [
                self.ext_node_vars[ext.address].waste_fluids
                for ext in self.problem.extension_nodes
                if ext.address in self.ext_node_vars
            ]
            self.model.Minimize(sum(regular_waste + ext_waste))

    # ------------------------------------------------------------------
    # 求解
    # ------------------------------------------------------------------

    def solve(self) -> Optional[OptimizationResult]:
        # DFMM ヒントの追加（有効な場合）
        if self.solver_cfg.use_dfmm_hints:
            self._add_dfmm_hints()

        print(f"\n--- Solving Extension-MTWM ({self.objective_mode}) ---")
        print(f"    拡張ノード数: {len(self.problem.extension_nodes)}")
        print(f"    workers={self.solver_cfg.num_workers}, "
              f"lin_level={self.solver_cfg.linearization_level}, "
              f"lin_products={self.solver_cfg.linearize_products}, "
              f"branching={self.solver_cfg.search_branching}")

        start_time = time.time()
        printer = SolutionPrinter()
        status = self.solver.Solve(self.model, printer)
        execution_time = time.time() - start_time

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
            print(f"Status: {status_str}, "
                  f"Objective (waste): {int(self.solver.ObjectiveValue())}, "
                  f"Time: {execution_time:.2f}s")
            return self._extract_solution(execution_time)
        else:
            print("No solution found.")
            return None

    # ------------------------------------------------------------------
    # 結果抽出
    # ------------------------------------------------------------------

    def _extract_solution(self, execution_time: float) -> OptimizationResult:
        """通常ノード + 拡張ノードの結果を抽出"""
        nodes_res = []
        total_waste = 0

        for addr, vars_obj in self.node_vars.items():
            if self.solver.Value(vars_obj.is_active):
                waste = (
                    self.solver.Value(vars_obj.waste_fluids)
                    if vars_obj.waste_fluids is not None else 0
                )
                total_waste += waste
                nodes_res.append(NodeFlowResult(
                    address=addr,
                    total_input=self.solver.Value(vars_obj.total_input),
                    concentration_state=[self.solver.Value(v) for v in vars_obj.R],
                    injected_reagent_volumes=[self.solver.Value(v) for v in vars_obj.r],
                    waste_fluids=waste,
                ))

        edges_res = []
        for (src_addr, dst_addr), var in self.edge_vars.items():
            vol = self.solver.Value(var)
            if vol > 0:
                edges_res.append(EdgeFlowResult(source=src_addr, target=dst_addr, volume=vol))

        # 拡張ノードの結果抽出
        ext_nodes_res = []
        for ext_node in self.problem.extension_nodes:
            ext_addr = ext_node.address
            ext_vars = self.ext_node_vars[ext_addr]

            if self.solver.Value(ext_vars.is_active):
                ext_waste = self.solver.Value(ext_vars.waste_fluids)
                total_waste += ext_waste

                # z 変数（どこに何単位送ったか）の抽出
                outgoing = []
                for (ea, dst_addr), z_var in self.ext_edge_vars.items():
                    if ea == ext_addr:
                        vol = self.solver.Value(z_var)
                        if vol > 0:
                            outgoing.append((dst_addr, vol))
                            edges_res.append(
                                EdgeFlowResult(
                                    source=ext_addr,   # type: ignore[arg-type]
                                    target=dst_addr,
                                    volume=vol,
                                )
                            )

                ext_nodes_res.append(ExtensionNodeFlowResult(
                    address=ext_addr,
                    input_1=ext_node.input_1,
                    input_2=ext_node.input_2,
                    concentration_state=[self.solver.Value(c) for c in ext_vars.C],
                    waste_fluids=ext_waste,
                    outgoing_volumes=outgoing,
                ))

        return OptimizationResult(
            objective_value=int(self.solver.ObjectiveValue()),
            total_waste_fluids=total_waste,
            nodes=nodes_res,
            edges=edges_res,
            execution_time=execution_time,
            extension_nodes=ext_nodes_res,
        )
