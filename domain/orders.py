def can_exec_order(team_cash: float, team_qty: float, side: str, qty: float, px: float, fees_bps: float):
    notional = qty * px
    fees = notional * (fees_bps / 10000.0)
    if side == "BUY":
        if team_cash >= notional + fees:
            return True, ""
        return False, "Cash insuficiente"
    elif side == "SELL":
        if team_qty >= qty:
            return True, ""
        return False, "Posición insuficiente"
    return False, "Lado de orden inválido"

def exec_order(team_id: str, bond_id: str, side: str, qty: float, px_exec: float, fees_bps: float, ronda: int):
    notional = qty * px_exec
    fees = notional * (fees_bps / 10000.0)
    return {
        "team_id": team_id,
        "bond_id": bond_id,
        "side": side,
        "qty": qty,
        "price_exec": px_exec,
        "fees": fees,
        "ronda": ronda,
    }
