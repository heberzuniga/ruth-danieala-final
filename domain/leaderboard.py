def compute_positions(orders: list[dict]):
    # Muy simple: BUY suma qty, SELL resta qty, agrupado por (team_id, bond_id)
    pos = {}
    for o in orders or []:
        key = (o.get("team_id"), o.get("bond_id"))
        qty = o.get("qty", 0.0) * (1 if o.get("side") == "BUY" else -1)
        pos[key] = pos.get(key, 0.0) + qty
    return pos  # dict[(team_id,bond_id)] -> qty

def compute_portfolio_value(positions_by_team: dict, prices_mid: dict, cash_inicial_by_team: dict):
    # Suma cash_inicial + Σ(qty * mid)
    vals = {}
    for (team_id, bond_id), qty in positions_by_team.items():
        mid = prices_mid.get(bond_id, 0.0)
        vals[team_id] = vals.get(team_id, 0.0) + qty * mid
    # add cash
    for t, cash in (cash_inicial_by_team or {}).items():
        vals[t] = vals.get(t, 0.0) + cash
    items = [{"team_id": t, "valor_portafolio": v} for t, v in vals.items()]
    items.sort(key=lambda x: x["valor_portafolio"], reverse=True)
    return items
