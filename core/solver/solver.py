import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from ortools.sat.python import cp_model
from core.solver.problem import MTWMProblem
from core.solver.dto import OptimizationResult, NodeFlowResult, EdgeFlowResult
from core.models import NodeAddress

@dataclass
class NodeVariables:
    """Or-Toolsの変数（IntVar等）を型安全に保持するクラス"""
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
        current_time = time.time()
        print(f"Solution #{self.solution_count}: Objective = {self.ObjectiveValue()}, Time = {current_time - self.start_time:.2f}s")


class MTWMSolver:
    def __init__(self, problem: MTWMProblem, objective_mode="waste_fluids"):
        self.problem = problem
        self.objective_mode = objective_mode
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        self.node_vars: Dict[NodeAddress, NodeVariables] = {}
        self.edge_vars: Dict[Tuple[NodeAddress, NodeAddress], cp_model.IntVar] = {}

        self._configure_solver()
        self._build_model()

    def _configure_solver(self):
        self.solver.parameters.num_workers = 16
        self.solver.parameters.max_time_in_seconds = 5000
        self.solver.parameters.log_search_progress = True
        self.solver.parameters.linearization_level = 0    # 線形化のレベルを下げる
        self.solver.parameters.boolean_encoding_level = 1 # 整数変数のブール変換レベル
        self.solver.parameters.max_num_cuts = 10000        # カット（枝刈り）の最大数
        self.solver.parameters.cut_level = 2              # カット生成の強度を最大化

    def _build_model(self):
        self._define_variables()
        self._set_initial_target_constraints()
        self._set_mass_conservation_constraints()
        self._set_concentration_constraints()
        self._set_mixer_capacity_and_activity_constraints()
        self._set_objective_function()
        self._set_ratio_sum_constraints()

    def _define_variables(self):
        for addr, meta in self.problem.nodes_metadata.items():
            m, l, k = addr.target_id, addr.level, addr.index
            f_val = meta.factor
            p_val = meta.droplet_weight
            
            vars_obj = NodeVariables()
            vars_obj.R = [self.model.NewIntVar(0, p_val, f"R_{m}_{l}_{k}_t{t}") for t in range(self.problem.num_reagents)]
            vars_obj.r = [self.model.NewIntVar(0, max(0, f_val - 1), f"r_{m}_{l}_{k}_t{t}") for t in range(self.problem.num_reagents)]
            vars_obj.total_input = self.model.NewIntVar(0, f_val, f"total_{m}_{l}_{k}")
            vars_obj.is_active = self.model.NewBoolVar(f"isActive_{m}_{l}_{k}")
            
            if not meta.is_leaf:
                vars_obj.waste_fluids = self.model.NewIntVar(0, f_val, f"waste_{m}_{l}_{k}")
                
            self.node_vars[addr] = vars_obj

        for dst_addr, src_addresses in self.problem.potential_sources_map.items():
            for src_addr in src_addresses:
                limit = self.problem.nodes_metadata[src_addr].factor
                name = f"edge_{src_addr.target_id}_{src_addr.level}_{src_addr.index}_to_{dst_addr.target_id}_{dst_addr.level}_{dst_addr.index}"
                self.edge_vars[(src_addr, dst_addr)] = self.model.NewIntVar(0, limit, name)

    def _set_initial_target_constraints(self):
        for m, target in enumerate(self.problem.targets):
            for addr, meta in self.problem.nodes_metadata.items():
                if addr.target_id == m and addr.level == 0:  
                    for t in range(self.problem.num_reagents):
                        self.model.Add(self.node_vars[addr].R[t] == target.ratios[t])

    def _set_mass_conservation_constraints(self):
        for dst_addr, meta in self.problem.nodes_metadata.items():
            inputs = list(self.node_vars[dst_addr].r) 
            
            for src_addr in self.problem.potential_sources_map.get(dst_addr, []):
                inputs.append(self.edge_vars[(src_addr, dst_addr)])
                
            self.model.Add(self.node_vars[dst_addr].total_input == sum(inputs))

    def _set_concentration_constraints(self):
        for dst_addr, meta_dst in self.problem.nodes_metadata.items():
            p_dst = meta_dst.droplet_weight
            f_dst = meta_dst.factor
            
            src_addresses = self.problem.potential_sources_map.get(dst_addr, [])
            if not src_addresses and meta_dst.is_leaf:
                for t in range(self.problem.num_reagents):
                    self.model.Add(self.node_vars[dst_addr].R[t] == self.node_vars[dst_addr].r[t])
                continue

            p_values = [self.problem.nodes_metadata[s].droplet_weight for s in src_addresses] + [p_dst]
            common_lcm = math.lcm(*p_values)
            
            for t in range(self.problem.num_reagents):
                lhs_scale = common_lcm // p_dst
                lhs_term = f_dst * self.node_vars[dst_addr].R[t] * lhs_scale
                
                rhs_terms = [self.node_vars[dst_addr].r[t] * common_lcm]
                
                for src_addr in src_addresses:
                    scale = common_lcm // self.problem.nodes_metadata[src_addr].droplet_weight
                    w_var = self.edge_vars[(src_addr, dst_addr)]
                    R_src = self.node_vars[src_addr].R[t]
                    
                    max_prod = self.problem.nodes_metadata[src_addr].factor * self.problem.nodes_metadata[src_addr].droplet_weight
                    prod_var = self.model.NewIntVar(0, max_prod, f"prod_{src_addr.target_id}_{src_addr.level}_{src_addr.index}_to_dst_t{t}")
                    self.model.AddMultiplicationEquality(prod_var, [w_var, R_src])
                    
                    rhs_terms.append(prod_var * scale)
                    
                self.model.Add(lhs_term == sum(rhs_terms))

    def _set_mixer_capacity_and_activity_constraints(self):
        for addr, meta in self.problem.nodes_metadata.items():
            f_val = meta.factor
            vars_obj = self.node_vars[addr]
            
            if addr.level == 0:
                self.model.Add(vars_obj.total_input == f_val)
                self.model.Add(vars_obj.is_active == 1)
            else:
                self.model.Add(vars_obj.total_input == f_val * vars_obj.is_active)
                
            if not meta.is_leaf:
                outgoing_edges = [var for (src, dst), var in self.edge_vars.items() if src == addr]
                total_used = sum(outgoing_edges) if outgoing_edges else 0
                
                if outgoing_edges:
                    self.model.Add(total_used >= 1).OnlyEnforceIf(vars_obj.is_active)
                    self.model.Add(total_used == 0).OnlyEnforceIf(vars_obj.is_active.Not())
                
                self.model.Add(vars_obj.waste_fluids == vars_obj.total_input - total_used)

    def _set_objective_function(self):
        if self.objective_mode == "waste_fluids":
            all_waste_vars = [v.waste_fluids for v in self.node_vars.values() if v.waste_fluids is not None]
            self.model.Minimize(sum(all_waste_vars))

    def solve(self) -> OptimizationResult | None:
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

    def _extract_solution(self) -> OptimizationResult:
        nodes_res = []
        total_waste = 0
        
        for addr, vars_obj in self.node_vars.items():
            if self.solver.Value(vars_obj.is_active):
                waste = self.solver.Value(vars_obj.waste_fluids) if vars_obj.waste_fluids is not None else 0
                total_waste += waste
                
                nodes_res.append(NodeFlowResult(
                    address=addr,
                    total_input=self.solver.Value(vars_obj.total_input),
                    concentration_state=[self.solver.Value(v) for v in vars_obj.R],
                    injected_reagent_volumes=[self.solver.Value(v) for v in vars_obj.r],
                    waste_fluids=waste
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
            edges=edges_res
        )
    
    def _set_ratio_sum_constraints(self):
        """冗長制約：各ノードの比率の合計は、その解像度(p)と一致する"""
        for addr, meta in self.problem.nodes_metadata.items():
            vars_obj = self.node_vars[addr]
            p_val = meta.droplet_weight  # 解像度 (p)
            
            # is_active == 1 なら合計は p_val、0 なら 0
            self.model.Add(sum(vars_obj.R) == p_val * vars_obj.is_active)