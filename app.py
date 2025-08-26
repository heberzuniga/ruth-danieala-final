import streamlit as st
import pandas as pd
import numpy as np
import io, csv, math
from datetime import datetime

# ==============================
# Helpers CSV robusto (coma/; | UTF-8/latin-1 | BOM)
# ==============================
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
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return io.StringIO(raw.decode(enc))
            except Exception:
                pass
        return io.StringIO(raw.decode(errors="ignore"))
    return io.StringIO(str(raw))

def _sniff(sample):
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",",";","\t","|"])
    except Exception:
        class _D(csv.Dialect):
            delimiter=","
            quotechar='"'
            doublequote=True
            skipinitialspace=True
            lineterminator="\n"
            quoting=csv.QUOTE_MINIMAL
        return _D

def load_bonds_csv(uploaded_or_text) -> pd.DataFrame:
    text = _to_text(uploaded_or_text)
    sample = text.read(4096); text.seek(0)
    dialect = _sniff(sample)
    reader = csv.reader(text, dialect)
    try:
        header = next(reader)
    except StopIteration:
        return pd.DataFrame()
    header = [(h or "").strip().lower() for h in header]
    rows = []
    for r in reader:
        if not any(str(x).strip() for x in r): continue
        r = list(r) + [""]*(len(header)-len(r)) if len(r)<len(header) else r[:len(header)]
        rows.append({header[i]: r[i] for i in range(len(header))})
    df = pd.DataFrame(rows)

    # columnas mínimas
    must = ["bond_id","nombre","valor_nominal","tasa_cupon_anual","frecuencia_anual","vencimiento_anios","spread_bps"]
    for c in must:
        if c not in df.columns: df[c] = ""

    # casts y normalizaciones
    def fnum(x, d=0.0):
        try:
            s = str(x).replace(",", ".").replace("%","").strip()
            return float(s) if s!="" else d
        except Exception:
            return d

    def fint(x, d=0):
        try:
            s = str(x).replace(",", ".").strip()
            return int(float(s)) if s!="" else d
        except Exception:
            return d

    def tf(s):
        s = str(s).strip().upper()
        return s in ("TRUE","1","SI","SÍ","YES","Y","T")

    df["bond_id"]            = df["bond_id"].map(lambda x: str(x).strip())
    df["valor_nominal"]      = df["valor_nominal"].map(lambda x: fnum(x, 1000))
    df["tasa_cupon_anual"]   = df["tasa_cupon_anual"].map(lambda x: fnum(x, 0.0))
    df["frecuencia_anual"]   = df["frecuencia_anual"].map(lambda x: fint(x, 2))
    df["vencimiento_anios"]  = df["vencimiento_anios"].map(lambda x: fnum(x, 3.0))
    df["spread_bps"]         = df["spread_bps"].map(lambda x: fnum(x, 0.0))
    if "callable" in df.columns:
        df["callable"] = df["callable"].map(tf)
    else:
        df["callable"] = False
    if "precio_call" not in df.columns: df["precio_call"] = np.nan
    return df

# ==============================
# Modelo de precios (MVP)
# ==============================
def price_bond_mid(row, ytm_anual: float, frac_anio: float, rounds_elapsed: int) -> float:
    Vn   = float(row["valor_nominal"])
    c    = float(row["tasa_cupon_anual"])
    f    = int(row["frecuencia_anual"])
    T0   = float(row["vencimiento_anios"])
    # Ajustar time-to-maturity según rondas transcurridas
    T    = max(0.0, T0 - rounds_elapsed * frac_anio)
    if T <= 0:  # al vencimiento, valor nominal
        return Vn
    C    = Vn * (c / f)
    i    = ytm_anual / f
    N    = max(1, math.ceil(T * f))  # pagos restantes
    # PV de cupones + principal
    pv_c = sum(C / ((1 + i) ** k) for k in range(1, N + 1))
    pv_p = Vn / ((1 + i) ** N)
    return float(pv_c + pv_p)

def bid_ask_from_mid(mid: float, bid_bp: float, ask_bp: float) -> tuple[float,float]:
    bid = mid * (1 - bid_bp/10_000)
    ask = mid * (1 + ask_bp/10_000)
    return float(bid), float(ask)

def effective_ytm(row, base_rate_anual: float, market_bps: float, idios_bps: float) -> float:
    return base_rate_anual + row["spread_bps"]/10_000 + market_bps/10_000 + idios_bps/10_000

# ==============================
# Propuesta de 3 eventos adaptativos
# ==============================
def propose_events(bonds_df: pd.DataFrame, e1_market_bps: int, e2_idios_bps: int, e3_delta_good_bps: int, e3_delta_rest_bps: int):
    """Devuelve lista de 3 eventos paramétricos y adaptativos al dataset."""
    hi = bonds_df.sort_values("spread_bps", ascending=False).iloc[0]["bond_id"]
    lo = bonds_df.sort_values("spread_bps", ascending=True).iloc[0]["bond_id"]
    return [
        {"round": 1, "tipo": "MARKET", "bond_id": None, "delta_tasa_bps": e1_market_bps, "impacto_bps": 0,
         "descripcion": f"Shock de tasa global {e1_market_bps:+} bps"},
        {"round": 2, "tipo": "IDIOS", "bond_id": hi, "delta_tasa_bps": 0, "impacto_bps": e2_idios_bps,
         "descripcion": f"Widening idiosincrático en {hi}: {e2_idios_bps:+} bps"},
        {"round": 3, "tipo": "MIXTO", "bond_id": lo, "delta_tasa_bps": 0, "impacto_bps": 0,
         "descripcion": f"Flight-to-quality: {lo} {e3_delta_good_bps:+} bps; resto {e3_delta_rest_bps:+} bps (y +liquidez)"}
    ]

# ==============================
# PNL y posiciones
# ==============================
def compute_positions(orders: list[dict]):
    pos = {}   # (team,bond) -> qty
    cash = {}  # team -> cash
    fees = {}  # team -> fees
    for od in orders:
        t = od["team"]; b = od["bond_id"]; side = od["side"]
        q = float(od["qty"]); px = float(od["price_exec"])
        fee = float(od["fees"])
        fees[t] = fees.get(t, 0.0) + fee
        if side == "BUY":
            cash[t] = cash.get(t, 100_000.0) - q*px - fee
            pos[(t,b)] = pos.get((t,b), 0.0) + q
        else:
            cash[t] = cash.get(t, 100_000.0) + q*px - fee
            pos[(t,b)] = pos.get((t,b), 0.0) - q
    # completar cash inicial si equipo no operó
    teams = set([od["team"] for od in orders])
    for t in teams:
        cash.setdefault(t, 100_000.0)
    return pos, cash, fees

def portfolio_value(teams, bonds_df, prices_dict, orders):
    """
    Versión robusta: nunca lanza KeyError; devuelve DF vacío con columnas esperadas si no hay datos.
    """
    pos, cash, fees = compute_positions(orders)
    values = []
    for t in teams:
        c = cash.get(t, 100_000.0)
        pv = c
        if bonds_df is not None and "bond_id" in bonds_df.columns:
            for b in bonds_df["bond_id"]:
                q = pos.get((t,b), 0.0)
                mid = prices_dict.get(b, {}).get("mid", np.nan)
                if not np.isnan(mid):
                    pv += q * mid
        values.append({"team": t, "valor_portafolio": round(pv,2), "cash": round(c,2)})
    df = pd.DataFrame(values)
    if df.empty or "valor_portafolio" not in df.columns:
        return pd.DataFrame(columns=["team","valor_portafolio","cash"])
    return df.sort_values("valor_portafolio", ascending=False).reset_index(drop=True)

# ==============================
# Estado inicial
# ==============================
APP_TITLE = "Misión Bonos — Competencia"
APP_VERSION = "1.0.1"

DEFAULTS = dict(
    # ---- NUEVO: persistencia de rol y equipo actual ----
    role="Moderador",
    current_team="",
    # ----------------------------------------------------
    game_code="MB-001",
    frac_anio=0.25,
    base_rate=0.00,
    bid_bp=10,
    ask_bp=10,
    fee_bps=5,
    round=0,             # 0 = antes de eventos; 1..3 después de cada publicación
    prices={},           # {bond_id: {mid,bid,ask}}
    orders=[],           # lista de dicts
    teams=set(),         # set de team_names
    bonds=None,
    events=None,
    liquidity_widen_bp=10 # ensanchamiento adicional en evento 3
)

st.set_page_config(page_title=APP_TITLE, layout="wide")

for k,v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k]=v
state = st.session_state

# ==============================
# Sidebar (rol & setup)
# ==============================
with st.sidebar:
    st.header("Controles")
    role = st.selectbox(
        "Rol",
        ["Moderador","Participante"],
        index=["Moderador","Participante"].index(state.get("role","Moderador")),
        key="role"  # <-- persistencia real del rol
    )
    state["game_code"] = st.text_input("Game Code", value=state["game_code"])
    st.caption("Cada equipo usa el mismo Game Code.")
    st.markdown("---")

st.title(f"{APP_TITLE} · v{APP_VERSION}")

# ==============================
# Moderador
# ==============================
def ui_moderator():
    st.subheader("Panel del Moderador")
    with st.expander("1) Escenario (CSV) — o usa un ejemplo", expanded=True):
        up = st.file_uploader(
            "CSV de bonos (cabeceras mínimas: bond_id,nombre,valor_nominal,tasa_cupon_anual,frecuencia_anual,vencimiento_anios,spread_bps,callable,precio_call)",
            type=["csv"]
        )
        colA, colB = st.columns(2)
        with colA:
            if st.button("Cargar CSV"):
                if not up:
                    st.warning("Sube un CSV o usa el ejemplo.")
                else:
                    try:
                        df = load_bonds_csv(up)
                        state.bonds = df
                        st.success(f"Cargados {len(df)} bonos.")
                    except Exception as e:
                        st.error("No se pudo leer el CSV.")
                        st.exception(e)
        with colB:
            if st.button("Usar ejemplo"):
                sample_csv = """bond_id,nombre,valor_nominal,tasa_cupon_anual,frecuencia_anual,vencimiento_anios,spread_bps,callable,precio_call,descripcion
B1,Bono Soberano 3y,1000,0.06,2,3,80,FALSE,,Core
B2,Bono Corp AAA 5y,1000,0.05,2,5,120,TRUE,1020,Callable
B3,Bono HY 4y,1000,0.08,4,4,300,FALSE,,High Yield
"""
                state.bonds = load_bonds_csv(sample_csv)
                st.success("Ejemplo cargado.")

        if state.bonds is not None:
            st.dataframe(state.bonds, use_container_width=True)

    with st.expander("2) Parámetros & Eventos", expanded=True):
        c1,c2,c3,c4 = st.columns(4)
        state.base_rate = c1.number_input("Tasa base anual", value=float(state.base_rate), step=0.01, format="%.2f")
        state.frac_anio = c2.selectbox("Fracción de año por ronda", options=[0.25,0.5,1.0], index=[0.25,0.5,1.0].index(state.frac_anio))
        state.bid_bp   = c3.number_input("Bid spread (bps)", value=int(state.bid_bp), step=1)
        state.ask_bp   = c4.number_input("Ask spread (bps)", value=int(state.ask_bp), step=1)
        c5,c6,c7 = st.columns(3)
        state.fee_bps  = c5.number_input("Comisión (bps)", value=int(state.fee_bps), step=1)
        state.liquidity_widen_bp = c6.number_input("Widening de liquidez en Evento 3 (bps)", value=int(state.liquidity_widen_bp), step=1)
        st.caption("Comisiones aplican a notional ejecutado; widening de liquidez ensancha bid/ask en el evento 3.")

        st.markdown("**Configura los 3 eventos**")
        e1 = st.slider("Evento 1: Shock de tasa (market, bps)", -150, 150, 50, step=5)
        e2 = st.slider("Evento 2: Widening idiosincrático (bps al bono con mayor spread)", -150, 300, 100, step=5)
        e3_good = st.slider("Evento 3: Mejora en bono más seguro (bps)", -150, 150, -30, step=5)
        e3_rest = st.slider("Evento 3: Castigo al resto (bps)", -150, 150, 30, step=5)

        if state.bonds is not None:
            state.events = propose_events(state.bonds, e1, e2, e3_good, e3_rest)
            st.dataframe(pd.DataFrame(state.events), use_container_width=True)

    with st.expander("3) Publicar evento / abrir trading", expanded=True):
        disabled = state.bonds is None or state.events is None
        c1, c2, c3 = st.columns(3)
        if c1.button("Publicar siguiente evento", disabled=disabled):
            publish_next_event()
        trading = c2.toggle("Trading ON", value=(state.get("trading_on", False) and state.round>0), disabled=(state.round==0))
        state.trading_on = trading
        if c3.button("Finalizar Juego (calcular ranking)", disabled=(state.round<3)):
            state.trading_on = False
            st.success("Juego finalizado. Ranking disponible abajo.")

    st.markdown("### Orders")
    st.dataframe(pd.DataFrame(state.orders) if state.orders else pd.DataFrame(columns=["ts","team","bond_id","side","qty","price_exec","fees","ronda"]), use_container_width=True, height=240)

    st.markdown("### Leaderboard (en vivo)")
    lb = compute_leaderboard_current()
    st.dataframe(lb, use_container_width=True)

def publish_next_event():
    """Calcula precios y avanza round (1..3)."""
    if state.bonds is None or state.events is None:
        st.warning("Carga bonos y define eventos primero."); return
    if state.round >= 3:
        st.info("Ya se publicaron los 3 eventos."); return

    evt = state.events[state.round]   # 0->1, 1->2, 2->3
    round_target = state.round + 1
    prices = {}
    widen = state.liquidity_widen_bp if round_target==3 else 0

    # función auxiliar para MIXTO
    def parse_good_rest():
        good_bps, rest_bps = -30, 30
        try:
            e = next(ev for ev in state.events if ev["tipo"]=="MIXTO")
            parts = e["descripcion"].split(":")[1]
            nums = [p for p in parts.replace("bps","").replace("+","").split() if p.replace("-","").isdigit()]
            if len(nums)>=2:
                good_bps = int(nums[0]); rest_bps = int(nums[1])
        except Exception:
            pass
        return good_bps, rest_bps

    # calcular precios
    for _,row in state.bonds.iterrows():
        market_bps = 0.0
        idios_bps  = 0.0
        if evt["tipo"]=="MARKET":
            market_bps = evt["delta_tasa_bps"]
        elif evt["tipo"]=="IDIOS":
            if row["bond_id"]==evt["bond_id"]:
                idios_bps = evt["impacto_bps"]
        elif evt["tipo"]=="MIXTO":
            lo = state.bonds.sort_values("spread_bps", ascending=True).iloc[0]["bond_id"]
            good_bps, rest_bps = parse_good_rest()
            idios_bps = good_bps if row["bond_id"]==lo else rest_bps

        ytm = effective_ytm(row, state.base_rate, market_bps, idios_bps)
        mid = price_bond_mid(row, ytm, state.frac_anio, rounds_elapsed=round_target-1)
        bid_bp = state.bid_bp + (widen if evt["tipo"]=="MIXTO" else 0)
        ask_bp = state.ask_bp + (widen if evt["tipo"]=="MIXTO" else 0)
        bid, ask = bid_ask_from_mid(mid, bid_bp, ask_bp)
        prices[row["bond_id"]] = {"mid": round(mid,2), "bid": round(bid,2), "ask": round(ask,2)}

    state.prices = prices
    state.round = round_target
    state.trading_on = True
    st.success(f"Evento {state.round} publicado: {evt['descripcion']}")

def compute_leaderboard_current():
    if state.bonds is None or not state.teams:
        return pd.DataFrame(columns=["team","valor_portafolio","cash"])
    prices_mid = {b: v for b,v in state.prices.items()}
    teams = list(state.teams) if state.teams else []
    return portfolio_value(teams, state.bonds, prices_mid, state.orders)

# ==============================
# Participante
# ==============================
def ui_participant():
    st.subheader("Panel del Participante")
    c1,c2 = st.columns(2)
    team = c1.text_input("Nombre de equipo", value=state.get("current_team",""), key="team_name")
    if c2.button("Registrar / Entrar"):
        if not team.strip():
            st.warning("Ingresa un nombre de equipo.")
        else:
            state.teams.add(team.strip())
            state.current_team = team.strip()  # <-- persistimos el equipo
            st.success(f"Equipo '{team}' registrado.")
    if state.get("current_team"):
        st.info(f"Equipo actual: **{state.current_team}**")

    st.caption("Cash inicial: 100,000 (moneda ficticia).")

    st.markdown("### Precios actuales")
    if state.round==0:
        st.info("Aún no hay evento publicado. Espera al Moderador.")
    else:
        dfp = pd.DataFrame.from_dict(state.prices, orient="index").reset_index().rename(columns={"index":"bond_id"})
        st.dataframe(dfp, use_container_width=True)

    st.markdown("### Órdenes")
    if not state.get("trading_on", False):
        st.warning("Trading está cerrado. Espera al Moderador.")
    else:
        team_ok = (state.get("current_team","").strip()!="") and (state.get("current_team") in state.teams)
        if not team_ok:
            st.info("Regístrate como equipo para operar.")
        else:
            if state.bonds is not None and state.prices:
                colA, colB, colC, colD = st.columns([2,1,1,1])
                bond_id = colA.selectbox("Bono", options=list(state.bonds["bond_id"]))
                side    = colB.selectbox("Side", options=["BUY","SELL"])
                qty     = colC.number_input("Cantidad", min_value=1, value=10, step=1)
                px_exec = state.prices[bond_id]["ask"] if side=="BUY" else state.prices[bond_id]["bid"]
                fee     = (qty * px_exec) * (state.fee_bps/10_000)
                colD.metric("Precio exec", f"{px_exec:,.2f}")
                if st.button("Enviar orden"):
                    team_name = state.get("current_team")
                    od = dict(ts=datetime.utcnow().isoformat(), team=team_name, bond_id=bond_id, side=side,
                              qty=qty, price_exec=px_exec, fees=round(fee,2), ronda=state.round)
                    state.orders.append(od)
                    st.success("Orden ejecutada.")

    st.markdown("### Mis posiciones / valor (mid)")
    team_name = state.get("current_team","")
    my = [od for od in state.orders if od["team"]==team_name]
    if my:
        pos, cash, _ = compute_positions(my)
        rows=[]
        for b in state.bonds["bond_id"]:
            rows.append(dict(bond_id=b, qty=pos.get((team_name,b),0.0), mid=state.prices.get(b,{}).get("mid",np.nan)))
        dfp = pd.DataFrame(rows)
        val = portfolio_value([team_name], state.bonds, state.prices, my)
        st.dataframe(dfp, use_container_width=True)
        st.info(f"Valor de portafolio: {val.iloc[0]['valor_portafolio']:,.2f} | Cash: {val.iloc[0]['cash']:,.2f}")
    else:
        st.caption("Sin órdenes aún.")

    st.markdown("### Mini-Leaderboard")
    lb = compute_leaderboard_current()
    st.dataframe(lb, use_container_width=True, height=240)

# ==============================
# Router principal
# ==============================
if role == "Moderador":
    ui_moderator()
else:
    ui_participant()

st.markdown("---")
st.subheader("Resultado final")
if state.round<3:
    st.caption("El ranking final aparece cuando el Moderador publica los 3 eventos y cierra el juego.")
else:
    st.success("Competencia finalizada.")
    final_lb = compute_leaderboard_current()
    st.dataframe(final_lb, use_container_width=True)
