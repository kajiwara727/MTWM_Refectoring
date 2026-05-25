from config import get_default_config
from core import build_complete_dfmm_tree, apply_auto_factors
from core.solver.extension_problem import ExtensionMTWMProblem
from collections import Counter

cfg = get_default_config()
targets = apply_auto_factors(cfg.targets, cfg.max_mixer_size)
trees = [build_complete_dfmm_tree(t, i) for i, t in enumerate(targets)]
prob = ExtensionMTWMProblem(targets=targets, tree_structures=trees, max_mixer_size=cfg.max_mixer_size)

src_map     = prob.potential_sources_map
ext_src_map = prob.extension_sources_map
num_r       = len(targets[0].ratios)

total_products = sum(len(v) * num_r for v in src_map.values())
ext_products   = sum(len(v) * num_r for v in ext_src_map.values())

print(f"Nodes          : {len(prob.nodes_metadata)}")
print(f"Sharing edges  : {sum(len(v) for v in src_map.values())}")
print(f"Extension nodes: {len(prob.extension_nodes)}")
print(f"Ext edges      : {sum(len(v) for v in ext_src_map.values())}")
print(f"Products(w*R)  : {total_products}  <- AddMultiplicationEquality")
print(f"Products(z*C)  : {ext_products}   <- AddMultiplicationEquality")
weights = Counter(m.droplet_weight for m in prob.nodes_metadata.values())
factors = Counter(m.factor         for m in prob.nodes_metadata.values())
print(f"Weight dist    : {dict(sorted(weights.items()))}")
print(f"Factor dist    : {dict(sorted(factors.items()))}  (w_max = factor-1)")
