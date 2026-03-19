import streamlit as st
import plotly.graph_objects as go
from model import run_simulation, run_zone_simulation

st.set_page_config(page_title="Bioreactor Digital Twin", layout="wide")
st.title("Bioreactor Digital Twin")
st.subheader("Vanillin Production from E. coli — Ferulic Acid Bioconversion")

mode = st.radio("Mode", ["Ideal Reactor (Perfect Mixing)", "Scale-up: Zone Model"], horizontal=True)

st.sidebar.header("Kinetic Parameters")
mu_max = st.sidebar.slider("Max growth rate µmax (1/hr)", 0.05, 0.5, 0.15, 0.01)
ks = st.sidebar.slider("Saturation constant Ks (g/L)", 0.01, 0.5, 0.05, 0.01)
yxs = st.sidebar.slider("Biomass yield Yxs (g/g)", 0.1, 0.8, 0.4, 0.05)
yps = st.sidebar.slider("Vanillin yield Yps (g/g)", 0.1, 1.0, 0.7, 0.05)
X0 = st.sidebar.slider("Initial biomass X0 (g/L)", 0.01, 0.2, 0.05, 0.01)
S0 = st.sidebar.slider("Initial ferulic acid S0 (g/L)", 0.5, 3.0, 1.1, 0.1)
t_end = st.sidebar.slider("Simulation time (hr)", 5.0, 40.0, 20.0, 1.0)

if mode == "Ideal Reactor (Perfect Mixing)":
    st.info("Single well-mixed bioreactor. E. coli converts ferulic acid (substrate) into vanillin (product) while growing.")

    t, X, S, P = run_simulation(mu_max, ks, yxs, yps, X0, S0, t_end)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=X, name="Biomass X (g/L)", line=dict(color="#2a9d8f", width=2)))
    fig.add_trace(go.Scatter(x=t, y=S, name="Ferulic Acid S (g/L)", line=dict(color="#e76f51", width=2)))
    fig.add_trace(go.Scatter(x=t, y=P, name="Vanillin P (g/L)", line=dict(color="#9b5de5", width=2)))
    fig.update_layout(xaxis_title="Time (hr)", yaxis_title="Concentration (g/L)",
                      legend=dict(x=0.7, y=0.9))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Final Biomass", f"{X[-1]:.3f} g/L")
    col2.metric("Ferulic Acid Remaining", f"{S[-1]:.3f} g/L")
    col3.metric("Vanillin Produced", f"{P[-1]:.3f} g/L")

else:
    st.info("The bioreactor is divided into spatial zones (top → impeller). Poor mixing creates ferulic acid gradients — cells in substrate-poor zones produce less vanillin. This is the scale-up risk.")

    st.subheader("Preset scenarios")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Lab scale (~1L) — well mixed", use_container_width=True):
            st.session_state.exchange_rate = 2.0
            st.session_state.n_zones = 3
    with col2:
        if st.button("Pilot scale (~100L) — moderate mixing", use_container_width=True):
            st.session_state.exchange_rate = 0.3
            st.session_state.n_zones = 3
    with col3:
        if st.button("Industrial scale (500L+) — poor mixing", use_container_width=True):
            st.session_state.exchange_rate = 0.02
            st.session_state.n_zones = 3

    st.sidebar.header("Zone Parameters")
    n_zones = st.sidebar.slider("Number of zones", 2, 5,
                                 st.session_state.get("n_zones", 3), 1)
    exchange_rate = st.sidebar.slider("Mixing intensity (exchange rate)", 0.01, 2.0,
                                       st.session_state.get("exchange_rate", 0.1), 0.01)

    t, zones = run_zone_simulation(mu_max, ks, yxs, yps, X0, n_zones, exchange_rate, t_end)

    zone_colors = ["#e63946", "#f4a261", "#2a9d8f", "#457b9d", "#6a4c93"]
    zone_names = ["Zone 1 (top)", "Zone 2 (bulk)", "Zone 3 (impeller)", "Zone 4", "Zone 5"]

    tab1, tab2 = st.tabs(["Vanillin Production", "Biomass Growth"])

    with tab1:
        fig = go.Figure()
        for i, zone in enumerate(zones):
            fig.add_trace(go.Scatter(
                x=t, y=zone['P'],
                name=zone_names[i],
                line=dict(color=zone_colors[i], width=2)
            ))
        fig.update_layout(xaxis_title="Time (hr)", yaxis_title="Vanillin (g/L)",
                          title="Vanillin production per zone")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig = go.Figure()
        for i, zone in enumerate(zones):
            fig.add_trace(go.Scatter(
                x=t, y=zone['X'],
                name=zone_names[i],
                line=dict(color=zone_colors[i], width=2)
            ))
        fig.update_layout(xaxis_title="Time (hr)", yaxis_title="Biomass X (g/L)",
                          title="Biomass growth per zone")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Scale-up impact")
    cols = st.columns(n_zones)
    for i, zone in enumerate(zones):
        with cols[i]:
            st.metric(zone_names[i], f"{zone['P'][-1]:.3f} g/L", label_visibility="visible")
            st.caption("vanillin")

    best = max(z['P'][-1] for z in zones)
    worst = min(z['P'][-1] for z in zones)
    loss = (best - worst) / best * 100 if best > 0 else 0
    if loss < 10:
        st.success(f"Vanillin yield loss: {loss:.1f}% — good mixing, zones nearly uniform.")
    elif loss < 25:
        st.warning(f"Vanillin yield loss: {loss:.1f}% — moderate heterogeneity. Scale-up risk present.")
    else:
        st.error(f"Vanillin yield loss: {loss:.1f}% — severe heterogeneity. Significant vanillin yield loss at scale.")