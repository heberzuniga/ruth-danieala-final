import streamlit as st
import pandas as pd
from ui.components import sort_safe, toast_ok, toast_error, table
from services.storage_models import parse_scenario_csv
from domain.events import effective_ytm
from domain.pricing import price_bond_mid, bid_ask_from_mid

def render_moderator(state: dict):
    st.subheader("Panel del Moderador")
    demo_mode = st.sidebar.checkbox("Modo demo (CSV local)", value=True, help="Usa assets/sample_escenario.csv en lugar de Google Sheets")
    uploaded = None
    if demo_mode:
        st.caption("Demo con CSV local")
        uploaded = st.file_uploader("Cargar escenario CSV", type=["csv"], key="csv_local")
    else:
        st.caption("(Próxima iteración) Cargar a Google Sheets")

    if uploaded:
        bonds, events = parse_scenario_csv(uploaded)
        state["bonds"] = bonds
        state["events"] = events
        toast_ok(f"Escenario cargado: {len(bonds)} bonos, {len(events)} eventos")
    else:
        # Mostrar cualquier dataset existente
        bonds = state.get("bonds", [])
        events = state.get("events", [])

    tab1, tab2, tab3 = st.tabs(["Bonos", "Eventos", "Publicar precios"])

    with tab1:
        dfb = pd.DataFrame(state.get("bonds", []))
        table(sort_safe(dfb, ["bond_id","nombre"]))

    with tab2:
        dfe = pd.DataFrame(state.get("events", []))
        table(sort_safe(dfe, ["round","tipo"]))

    with tab3:
        # Publicación simplificada: calcula y_efectiva y precios mid/bid/ask por ronda actual
        rondas_totales = state.setdefault("rondas_totales", 6)
        ronda_actual = state.setdefault("ronda_actual", 1)
        bid_bp = state.setdefault("bid_bp", 20)
        ask_bp = state.setdefault("ask_bp", 20)
        fraccion_anio = state.setdefault("fraccion_anio", 0.25)
        base_rate = state.setdefault("tasa_base", 0.0)

        st.markdown(f"**Ronda actual:** {ronda_actual} / {rondas_totales}")
        if st.button("Publicar precios de la ronda", type="primary"):
            prices = []
            bonds = state.get("bonds", [])
            events = state.get("events", [])
            # Calcular deltas de la ronda
            delta_market_bps = sum(e.get("delta_tasa_bps",0) for e in events if e.get("round")==ronda_actual and e.get("tipo")=="MARKET")
            idios_map = {}
            for e in events:
                if e.get("round")==ronda_actual and e.get("tipo")=="IDIOS":
                    bid_ = e.get("bond_id")
                    idios_map[bid_] = idios_map.get(bid_, 0.0) + float(e.get("impacto_bps",0))

            for b in bonds:
                ytm = effective_ytm(base_rate, b.get("spread_bps",0), delta_market_bps, idios_map.get(b.get("bond_id"), 0.0))
                mid = price_bond_mid(
                    valor_nominal=b.get("valor_nominal",1000.0),
                    tasa_cupon_anual=b.get("tasa_cupon_anual",0.0),
                    frecuencia_anual=b.get("frecuencia_anual",2),
                    vencimiento_anios=b.get("vencimiento_anios",1.0),
                    ytm_anual=ytm
                )
                bid, ask = bid_ask_from_mid(mid, bid_bp, ask_bp)
                prices.append({"ronda": ronda_actual, "bond_id": b.get("bond_id"), "y_efectiva": ytm, "precio_mid": mid, "precio_bid": bid, "precio_ask": ask})
            state["prices"] = prices
            toast_ok(f"Precios publicados para ronda {ronda_actual}")

        table(pd.DataFrame(state.get("prices", [])))
