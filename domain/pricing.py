import math

def price_bond_mid(valor_nominal: float, tasa_cupon_anual: float, frecuencia_anual: int,
                   vencimiento_anios: float, ytm_anual: float) -> float:
    """Precio teórico MID por DCF con YTM efectiva por periodo.
    Simplificado: N = ceil(vencimiento_anios * frecuencia_anual); i = ytm_anual / frecuencia_anual.
    """
    if frecuencia_anual <= 0:
        return valor_nominal
    N = max(0, math.ceil(max(0.0, vencimiento_anios) * frecuencia_anual))
    i = ytm_anual / frecuencia_anual
    C = valor_nominal * (tasa_cupon_anual / frecuencia_anual)
    pv_coupons = 0.0
    for k in range(1, N + 1):
        pv_coupons += C / ((1 + i) ** k)
    pv_principal = valor_nominal / ((1 + i) ** N) if N > 0 else valor_nominal
    return pv_coupons + pv_principal

def bid_ask_from_mid(mid: float, bid_bp: float, ask_bp: float):
    b = mid * (1 - (bid_bp / 10000.0))
    a = mid * (1 + (ask_bp / 10000.0))
    return b, a
