import csv, io

EXPECTED_BOND_COLS = ["bond_id","nombre","valor_nominal","tasa_cupon_anual",
                      "frecuencia_anual","vencimiento_anios","spread_bps",
                      "callable","precio_call","descripcion"]
EXPECTED_EVENT_COLS = ["round","tipo","bond_id","delta_tasa_bps","impacto_bps","descripcion"]

def _to_text(file_like):
    if isinstance(file_like, str):
        return io.StringIO(file_like)
    raw = None
    if hasattr(file_like, "getvalue"):
        raw = file_like.getvalue()
    elif hasattr(file_like, "read"):
        raw = file_like.read()
    if raw is None:
        return io.StringIO("")
    if isinstance(raw, bytes):
        for enc in ("utf-8-sig","utf-8","latin-1"):
            try:
                return io.StringIO(raw.decode(enc))
            except Exception:
                continue
        return io.StringIO(raw.decode(errors="ignore"))
    return io.StringIO(str(raw))

def _sniff(sample):
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",",";","\t","|"])
    except Exception:
        class _D(csv.Dialect):
            delimiter = ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL
        return _D

def _norm(h): 
    return (h or "").strip().lower()

def parse_scenario_csv(file_like):
    text = _to_text(file_like)
    sample = text.read(4096)
    text.seek(0)
    dialect = _sniff(sample)
    reader = csv.reader(text, dialect)

    try:
        header = next(reader)
    except StopIteration:
        return [], []
    header = [_norm(h) for h in header]

    def row_to_dict(row):
        if len(row) < len(header):
            row += [""] * (len(header) - len(row))
        elif len(row) > len(header):
            row = row[:len(header)]
        return {header[i]: (row[i].strip() if isinstance(row[i], str) else row[i]) for i in range(len(header))}

    bonds, events = [], []
    for raw in reader:
        if not any(str(x).strip() for x in raw):
            continue
        row = row_to_dict(raw)
        t = _norm(row.get("type",""))
        if not t and row.get("bond_id") and row.get("nombre"):
            t = "bond"

        def _f(x, d=0.0):
            try: return float(str(x).replace(",", ".").strip())
            except Exception: return float(d)
        def _i(x, d=0):
            try: return int(float(str(x).replace(",", ".").strip()))
            except Exception: return int(d)

        if t == "bond":
            callable_raw = str(row.get("callable","")).strip().upper()
            bonds.append({
                "bond_id": row.get("bond_id","").strip(),
                "nombre": row.get("nombre","").strip(),
                "valor_nominal": _f(row.get("valor_nominal",1000),1000),
                "tasa_cupon_anual": _f(row.get("tasa_cupon_anual",0),0),
                "frecuencia_anual": _i(row.get("frecuencia_anual",2),2),
                "vencimiento_anios": _f(row.get("vencimiento_anios",1),1),
                "spread_bps": _f(row.get("spread_bps",0),0),
                "callable": callable_raw in ("TRUE","1","SI","YES","Y","T"),
                "precio_call": (_f(row.get("precio_call",0),0) if row.get("precio_call") not in (None,"") else None),
                "descripcion": row.get("descripcion",""),
            })
        elif t in ("market","idios","idiosincratico","idiosincrático"):
            tipo = "MARKET" if t == "market" else "IDIOS"
            events.append({
                "round": _i(row.get("round",1),1),
                "tipo": tipo,
                "bond_id": (row.get("bond_id") or "").strip() or None,
                "delta_tasa_bps": _f(row.get("delta_tasa_bps",0),0),
                "impacto_bps": _f(row.get("impacto_bps",0),0),
                "descripcion": row.get("descripcion",""),
                "publicado": False,
            })
    return bonds, events
