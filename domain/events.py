def effective_ytm(base_rate_anual: float, spread_bps: float, delta_market_bps: float, idios_bps: float) -> float:
    return (base_rate_anual
            + spread_bps / 10000.0
            + delta_market_bps / 10000.0
            + idios_bps / 10000.0)
