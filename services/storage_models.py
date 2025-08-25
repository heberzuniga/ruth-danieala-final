import csv
import io

EXPECTED_BOND_COLS = ["bond_id","nombre","valor_nominal","tasa_cupon_anual","frecuencia_anual","vencimiento_anios","spread_bps","callable","precio_call","descripcion"]
EXPECTED_EVENT_COLS = ["round","tipo","bond_id","delta_tasa_bps","impacto_bps","descripcion"]

def parse_scenario_csv(file_like) -> tuple[list[dict], list[dict]]:
    """Devuelve (bonds, events). Soporta el CSV unificado con columna 'type'."""
    if not hasattr(file_like, "read"):
        file_like = io.StringIO(file_like)
    reader = csv.DictReader(file_like)
    bonds, events = [], []
    for row in reader:
        t = (row.get("type") or "").strip().upper()
        if t == "BOND":
            bonds.append({
                "bond_id": row.get("bond_id","").strip(),
                "nombre": row.get("nombre","").strip(),
                "valor_nominal": float(row.get("valor_nominal", 1000) or 1000),
                "tasa_cupon_anual": float(row.get("tasa_cupon_anual", 0) or 0),
                "frecuencia_anual": int(float(row.get("frecuencia_anual", 2) or 2)),
                "vencimiento_anios": float(row.get("vencimiento_anios", 1) or 1),
                "spread_bps": float(row.get("spread_bps", 0) or 0),
                "callable": (str(row.get("callable","")).strip().upper() == "TRUE"),
                "precio_call": float(row.get("precio_call", 0) or 0) if row.get("precio_call") else None,
                "descripcion": row.get("descripcion",""),
            })
        elif t in ("MARKET","IDIOS"):
            events.append({
                "round": int(float(row.get("round", 1) or 1)),
                "tipo": t,
                "bond_id": (row.get("bond_id") or "").strip() or None,
                "delta_tasa_bps": float(row.get("delta_tasa_bps", 0) or 0),
                "impacto_bps": float(row.get("impacto_bps", 0) or 0),
                "descripcion": row.get("descripcion",""),
                "publicado": False,
            })
    return bonds, events
