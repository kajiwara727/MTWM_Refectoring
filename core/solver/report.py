def print_solution_report(solution: dict, num_reagents: int):
    """
    ソルバーが返した解（辞書）を見やすく整形して出力します。
    """
    if not solution:
        print("表示する解がありません。")
        return

    print("\n" + "="*50)
    print(" " * 15 + "MTWM Optimization Report")
    print("="*50)
    
    print(f"[Summary]")
    print(f"  Objective Value       : {solution['objective_value']}")
    print(f"  Total Waste Fluids    : {solution['total_waste_fluids']}")
    print(f"  Total Active Nodes    : {len(solution['nodes'])}")
    
    # 全体の試薬使用量を計算
    total_reagents_used = [0] * num_reagents
    for node in solution['nodes']:
        for t, r_vol in enumerate(node['r']):
            total_reagents_used[t] += r_vol
            
    print(f"  Total Reagents Used   : {total_reagents_used} (Sum: {sum(total_reagents_used)})")
    
    print("\n[Active Nodes Details]")
    # ターゲット(m) -> レベル(l) の順で見やすくソート
    sorted_nodes = sorted(solution['nodes'], key=lambda x: (x['id'][0], x['id'][1], x['id'][2]))
    
    for node in sorted_nodes:
        m, l, k = node['id']
        node_name = f"Target {m} / Level {l} / Node {k}"
        
        print(f"  - {node_name}")
        print(f"      Total Input  : {node['total_input']}")
        print(f"      State (R)    : {node['R']}")
        
        # 注入された試薬がある場合のみ表示
        used_reagents = [f"t{t}:{vol}" for t, vol in enumerate(node['r']) if vol > 0]
        if used_reagents:
            print(f"      Reagents (r) : {', '.join(used_reagents)}")
            
        if 'waste_fluids' in node:
            print(f"      Waste Fluids : {node['waste_fluids']}")
        print("")
        
    print("="*50 + "\n")