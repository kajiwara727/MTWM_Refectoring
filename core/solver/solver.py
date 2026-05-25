# core/solver/solver.py
"""
MTWM CP-SAT ソルバー。

チューニングの要点:
  1. linearization_level = 2
       AddMultiplicationEquality に対して LP 緩和（McCormick エンベロープ）が
       自動生成される。0 にすると LP が全く使えず極端に遅くなる。

  2. w*R の手動二値展開 (linearize_products=True)
       w ∈ {0..f-1} を二値ビット b_i に分解し、
       b_i * R を OnlyEnforceIf で完全線形化する。
       AddMultiplicationEquality より LP 緩和が tight → 枝刈り効率が上がる。

  3. DFMM ヒント (use_dfmm_hints=True)
       DFMM の試薬割り当て (reagent_dispensations) を初期解ヒントとして渡す。
       実行可能解の発見が早まり、上界を素早く確定できる。

  4. search_branching = PORTFOLIO_WITH_QUICK_RESTART
       汎用的に良い分岐戦略。大規模では LP_SEARCH(3) も有効。
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from core.solver.problem import MTWMProblem
from core.solver.solver_config import SolverConfig
from core.solver.dto import OptimizationResult, NodeFlowResult, EdgeFlowResult
from core.models import NodeAddress


@dataclass
class NodeVariables:
    """Or-Tools の変数を型安全に保持するクラス"""
    R: List[cp_model.IntVar] = field(default_factory=list)
    r: List[cp_model.IntVar] = field(default_factory=list)
    total_input: Optional[cp_model.IntVar] = None
    is_active: Optional[cp_model.IntVar] = None
    waste_fluids: Optional[cp_model.IntVar] = None


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.solution_count = 0
        self.start_time = time.time()

    def on_solution_callback(self):
        self.solution_count += 1
        elapsed = time.time() - self.start_time
        print(f"  Solution #{self.solution_count}: "
              f"Objective = {self.ObjectiveValue():.0f},  "
              f"Time = {elapsed:.2f}s")


class MTWMSolver:
    def __init__(
        self,
        problem: MTWMProblem,
        objective_mode: str = "waste_fluids",
        solver_config: Optional[SolverConfig] = None,
    ):
        self.problem = problem
        self.objective_mode = objective_mode
        self.solver_cfg = solver_config or SolverConfig.default_mtwm()

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        self.node_vars: Dict[NodeAddress, NodeVariables] = {}
        self.edge_vars: Dict[Tuple[NodeAddress, NodeAddress], cp_model.IntVar] = {}

        self._configure_solver()
        self._build_model()

    # ------------------------------------------------------------------
    # ソルバー設定
    # ------------------------------------------------------------------

    def _configure_solver(self) -> None:
        cfg = self.solver_cfg
        p = self.solver.parameters

        p.num_workers = cfg.num_workers
        p.max_time_in_seconds = cfg.max_time_seconds
        p.log_search_progress = cfg.log_search_progress

        # ★ 最重要: LP 緩和を有効にする（0 はデフォルト設定で最悪）
        p.linearization_level = cfg.linearization_level

        # ★ 分岐戦略
        p.search_branching = cfg.search_branching

        # カット生成（CP-SAT では控えめが良いことが多い）
        p.max_num_cuts = 1000
        p.cut_level = 1

    # ------------------------------------------------------------------
    # モデル構築
    # ------------------------------------------------------------------

    def _build_model(self) -> None:
        self._define_variables()
        self._set_initial_target_constraints()
        self._set_mass_conservation_constraints()
        self._set_concentration_constraints()
        self._set_mixer_capacity_and_activity_constraints()
        self._set_objective_function()
        self._set_ratio_sum_constraints()

    def _define_variables(self) -> None:
        for addr, meta in self.problem.nodes_metadata.items():
            m, l, k = addr.target_id, addr.level, addr.index
            f_val = meta.factor
            p_val = meta.droplet_weight

            vars_obj = NodeVariables()
            vars_obj.R = [
                self.model.NewIntVar(0, p_val, f"R_{m}_{l}_{k}_t{t}")
                for t in range(self.problem.num_reagents)
            ]
            vars_obj.r = [
                self.model.NewIntVar(0, max(0, f_val - 1), f"r_{m}_{l}_{k}_t{t}")
                for t in range(self.problem.num_reagents)
            ]
            vars_obj.total_input = self.model.NewIntVar(0, f_val, f"total_{m}_{l}_{k}")
            vars_obj.is_active   = self.model.NewBoolVar(f"isActive_{m}_{l}_{k}")

            if not meta.is_leaf:
                vars_obj.waste_fluids = self.model.NewIntVar(0, f_val, f"waste_{m}_{l}_{k}")

            self.node_vars[addr] = vars_obj

        for dst_addr, src_addresses in self.problem.potential_sources_map.items():
            for src_addr in src_addresses:
                limit = self.problem.nodes_metadata[src_addr].factor
                name = (
                    f"edge_{src_addr.target_id}_{src_addr.level}_{src_addr.index}"
                    f"_to_{dst_addr.target_id}_{dst_addr.level}_{dst_addr.index}"
                )
                self.edge_vars[(src_addr, dst_addr)] = self.model.NewIntVar(0, limit, name)

    def _set_initial_target_constraints(self) -> None:
        for m, target in enumerate(self.problem.targets):
            for addr, meta in self.problem.nodes_metadata.items():
                if addr.target_id == m and addr.level == 0:
                    for t in range(self.problem.num_reagents):
                        self.model.Add(self.node_vars[addr].R[t] == target.ratios[t])

    def _set_mass_conservation_constraints(self) -> None:
        for dst_addr in self.problem.nodes_metadata:
            inputs = list(self.node_vars[dst_addr].r)
            for src_addr in self.problem.potential_sources_map.get(dst_addr, []):
                inputs.append(self.edge_vars[(src_addr, dst_addr)])
            self.model.Add(self.node_vars[dst_addr].total_input == sum(inputs))

    def _set_concentration_constraints(self) -> None:
        """
        濃度整合性制約。
        linearize_products=True の場合、w*R 積を二値展開で線形化する。
        """
        use_lin = self.solver_cfg.linearize_products

        for dst_addr, meta_dst in self.problem.nodes_metadata.items():
            p_dst = meta_dst.droplet_weight
            f_dst = meta_dst.factor

            src_addresses = self.problem.potential_sources_map.get(dst_addr, [])

            if not src_addresses and meta_dst.is_leaf:
                for t in range(self.problem.num_reagents):
                    self.model.Add(
                        self.node_vars[dst_addr].R[t] == self.node_vars[dst_addr].r[t]
                    )
                continue

            p_values = [self.problem.nodes_metadata[s].droplet_weight
                        for s in src_addresses] + [p_dst]
            common_lcm = math.lcm(*p_values)

            for t in range(self.problem.num_reagents):
                lhs_scale = common_lcm // p_dst
                lhs_term  = f_dst * self.node_vars[dst_addr].R[t] * lhs_scale
                rhs_terms = [self.node_vars[dst_addr].r[t] * common_lcm]

                for src_addr in src_addresses:
                    meta_src = self.problem.nodes_metadata[src_addr]
                    scale    = common_lcm // meta_src.droplet_weight
                    w_var    = self.edge_vars[(src_addr, dst_addr)]
                    R_src    = self.node_vars[src_addr].R[t]
                    w_max    = meta_src.factor       # edge bound は factor
                    R_max    = meta_src.droplet_weight

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

                self.model.Add(lhs_term == sum(rhs_terms))

    def _set_mixer_capacity_and_activity_constraints(self) -> None:
        for addr, meta in self.problem.nodes_metadata.items():
            f_val    = meta.factor
            vars_obj = self.node_vars[addr]

            if addr.level == 0:
                self.model.Add(vars_obj.total_input == f_val)
                self.model.Add(vars_obj.is_active == 1)
            else:
                self.model.Add(vars_obj.total_input == f_val * vars_obj.is_active)

            if not meta.is_leaf:
                outgoing = [var for (src, _dst), var in self.edge_vars.items()
                            if src == addr]
                total_used = sum(outgoing) if outgoing else 0

                if outgoing:
                    self.model.Add(total_used >= 1).OnlyEnforceIf(vars_obj.is_active)
                    self.model.Add(total_used == 0).OnlyEnforceIf(vars_obj.is_active.Not())

                self.model.Add(vars_obj.waste_fluids == vars_obj.total_input - total_used)

    def _set_objective_function(self) -> None:
        if self.objective_mode == "waste_fluids":
            all_waste = [v.waste_fluids for v in self.node_vars.values()
                         if v.waste_fluids is not None]
            self.model.Minimize(sum(all_waste))

    def _set_ratio_sum_constraints(self) -> None:
        for addr, meta in self.problem.nodes_metadata.items():
            vars_obj = self.node_vars[addr]
            self.model.Add(sum(vars_obj.R) == meta.droplet_weight * vars_obj.is_active)

    # ------------------------------------------------------------------
    # ヘルパー: w*R の線形化（二値展開）
    # ------------------------------------------------------------------

    def _add_linear_product(
        self,
        prod_var: cp_model.IntVar,
        w_var:    cp_model.IntVar,
        w_max:    int,
        R_var:    cp_model.IntVar,
        R_max:    int,
        name:     str,
    ) -> None:
        """
        prod = w * R を二値展開で完全線形化する。

        w ∈ [0, w_max]:
          - w_max == 0: prod = 0 (定数)
          - w_max == 1: w は bool 相当 → OnlyEnforceIf で直接線形化
          - w_max >= 2: w を 2 進数ビットに分解し各ビット×R を線形化

        LP 緩和が完全 (tight) になるため、AddMultiplicationEquality より
        探索効率が高い。ただし変数・制約数は増える。
        """
        if w_max == 0:
            self.model.Add(prod_var == 0)
            return

        if w_max == 1:
            # w ∈ {0, 1}: BoolVar として扱う
            b = self.model.NewBoolVar(f"{name}_b")
            self.model.Add(w_var == b)
            self.model.Add(prod_var == 0).OnlyEnforceIf(b.Not())
            self.model.Add(prod_var == R_var).OnlyEnforceIf(b)
            return

        # w_max >= 2: 二値ビット分解
        num_bits = w_max.bit_length()   # ⌈log2(w_max+1)⌉
        bits = [self.model.NewBoolVar(f"{name}_b{i}") for i in range(num_bits)]

        # w = Σ 2^i * b_i
        self.model.Add(w_var == sum((1 << i) * bits[i] for i in range(num_bits)))
        # w ≤ w_max（2^num_bits - 1 > w_max の場合のみ必要）
        if (1 << num_bits) - 1 > w_max:
            self.model.Add(w_var <= w_max)

        # aux_i = b_i * R_var （OnlyEnforceIf で線形化）
        aux_list = []
        for i, bit in enumerate(bits):
            aux = self.model.NewIntVar(0, R_max, f"{name}_a{i}")
            self.model.Add(aux == 0).OnlyEnforceIf(bit.Not())
            self.model.Add(aux == R_var).OnlyEnforceIf(bit)
            aux_list.append(aux)

        # prod = Σ 2^i * aux_i
        self.model.Add(prod_var == sum((1 << i) * aux_list[i] for i in range(num_bits)))

    # ------------------------------------------------------------------
    # DFMM ヒント（初期解の高速発見）
    # ------------------------------------------------------------------

    def _add_dfmm_hints(self) -> None:
        """
        DFMM の試薬割り当て (reagent_dispensations) を初期解ヒントとして登録する。
        reagent_dispensations が空のノード（スケルトンツリー）は無視する。
        """
        for tree in self.problem.tree_structures:
            for addr, node in tree.items():
                if addr not in self.node_vars:
                    continue
                vars_obj = self.node_vars[addr]

                # is_active ヒント: DFMM は全ノードを使う
                self.model.AddHint(vars_obj.is_active, 1)

                # r[t] ヒント: DFMM 割り当てから直接注入量を推定
                if node.reagent_dispensations:
                    for t in range(self.problem.num_reagents):
                        hint_r = node.reagent_dispensations.count(t)
                        self.model.AddHint(vars_obj.r[t], hint_r)

    # ------------------------------------------------------------------
    # 求解
    # ------------------------------------------------------------------

    def solve(self) -> Optional[OptimizationResult]:
        # ヒントの追加（有効な場合）
        if self.solver_cfg.use_dfmm_hints:
            self._add_dfmm_hints()

        print(f"\n--- Solving MTWM ({self.objective_mode}) ---")
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

    def _extract_solution(self, execution_time: float) -> OptimizationResult:
        nodes_res = []
        total_waste = 0

        for addr, vars_obj in self.node_vars.items():
            if self.solver.Value(vars_obj.is_active):
                waste = (self.solver.Value(vars_obj.waste_fluids)
                         if vars_obj.waste_fluids is not None else 0)
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

        return OptimizationResult(
            objective_value=int(self.solver.ObjectiveValue()),
            total_waste_fluids=total_waste,
            nodes=nodes_res,
            edges=edges_res,
            execution_time=execution_time,
        )
