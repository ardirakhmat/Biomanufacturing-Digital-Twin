import streamlit as st
import plotly.graph_objects as go
from model import run_simulation, run_zone_simulation

st.set_page_config(page_title="Bioreactor Digital Twin", layout="wide")

st.markdown("""
<style>
/* Enlarge all sidebar slider labels */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] p {
    font-size: 17px !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] h2 {
    font-size: 20px !important;
}
</style>
""", unsafe_allow_html=True)
st.title("Bioreactor Digital Twin")
st.subheader("Vanillin Production from E. coli — Ferulic Acid Bioconversion")

mode = st.radio("Mode", ["Ideal Reactor (Perfect Mixing)", "Scale-up"], horizontal=True)

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

elif mode == "Scale-up":

    if st.session_state.get("cfd_done"):
        st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)
        st.image("cfd_result.png", use_container_width=True)
        if st.button("← Back"):
            st.session_state.cfd_done = False
            st.rerun()
        st.stop()

    st.info("The bioreactor is divided into spatial zones. Poor mixing creates ferulic acid gradients — cells in substrate-poor zones produce less vanillin. This is the scale-up risk.")

    # Default to lab scale on first entry into zone mode
    if "preset" not in st.session_state:
        st.session_state.preset = "lab"
        st.session_state.exchange_rate = 2.0
        st.session_state.n_zones = 5

    st.subheader("Preset scenarios")

    preset = st.session_state.get("preset", None)

    preset_text = {
        "lab":        "Lab scale (~1L) — well mixed",
        "pilot":      "Pilot scale (~100L) — moderate mixing",
        "industrial": "Industrial scale (500L+) — poor mixing",
    }
    active_text = preset_text.get(preset, "")

    # Base font size for all preset buttons
    base_css = (
        'div[data-testid="stHorizontalBlock"] button {'
        'font-size: 19px !important;}'
    )
    active_css = ""
    if active_text:
        col_index = list(preset_text.keys()).index(preset) + 1
        active_css = (
            f'div[data-testid="stHorizontalBlock"] '
            f'> div:nth-child({col_index}) '
            f'button {{'
            f'background-color: #1a73e8 !important;'
            f'color: #ffffff !important;'
            f'border-color: #1a73e8 !important;'
            f'font-weight: 700 !important;'
            f'font-size: 19px !important;}}'
        )
    st.markdown(f"<style>{base_css}{active_css}</style>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Lab scale (~1L) — well mixed", key="btn_lab", use_container_width=True):
            st.session_state.exchange_rate = 2.0
            st.session_state.n_zones = 5
            st.session_state.preset = "lab"
            st.rerun()
    with col2:
        if st.button("Pilot scale (~100L) — moderate mixing", key="btn_pilot", use_container_width=True):
            st.session_state.exchange_rate = 0.3
            st.session_state.n_zones = 5
            st.session_state.preset = "pilot"
            st.rerun()
    with col3:
        if st.button("Industrial scale (500L+) — poor mixing", key="btn_industrial", use_container_width=True):
            st.session_state.exchange_rate = 0.02
            st.session_state.n_zones = 5
            st.session_state.preset = "industrial"
            st.rerun()

    st.sidebar.header("Zone Parameters")
    n_zones = st.sidebar.slider("Number of zones", 2, 5,
                                 st.session_state.get("n_zones", 3), 1)

    st.sidebar.markdown("**Mixing intensity (exchange rate)**")
    if "exchange_rate" not in st.session_state:
        st.session_state.exchange_rate = 0.1

    sb_col1, sb_col2, sb_col3 = st.sidebar.columns([1, 4, 1])
    with sb_col1:
        if st.button("−", key="er_minus"):
            st.session_state.exchange_rate = round(max(0.01, st.session_state.exchange_rate - 0.01), 2)
            st.rerun()
    with sb_col3:
        if st.button("+", key="er_plus"):
            st.session_state.exchange_rate = round(min(2.0, st.session_state.exchange_rate + 0.01), 2)
            st.rerun()
    with sb_col2:
        exchange_rate = st.slider(
            "", 0.01, 2.0,
            value=st.session_state.exchange_rate,
            step=0.01,
            label_visibility="collapsed"
        )
        # Slider always wins if user drags it
        if exchange_rate != st.session_state.exchange_rate:
            st.session_state.exchange_rate = exchange_rate

    # Always read from session state so +/- button reruns are reflected
    exchange_rate = st.session_state.exchange_rate

    # Clear preset label only if the slider was manually dragged (not +/- buttons)
    _preset_params = {"lab": (2.0, 5), "pilot": (0.3, 5), "industrial": (0.02, 5)}
    _current = st.session_state.get("preset")
    _slider_dragged = exchange_rate != st.session_state.get("exchange_rate", exchange_rate)
    if _current and _slider_dragged and _preset_params.get(_current) != (exchange_rate, n_zones):
        st.session_state.preset = None

    t, zones = run_zone_simulation(mu_max, ks, yxs, yps, X0, S0, n_zones, exchange_rate, t_end)

    zone_colors_hex = ["#e63946", "#f4a261", "#2a9d8f", "#457b9d", "#6a4c93"]
    _base_names = ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"]
    zone_names = [
        f"{_base_names[i]} (impeller)" if i == n_zones - 1 else _base_names[i]
        for i in range(n_zones)
    ]

    # ── Compute loss early so both row 2 columns can use it ─────────────────
    best = max(z['P'][-1] for z in zones)
    worst = min(z['P'][-1] for z in zones)
    loss = (best - worst) / best * 100 if best > 0 else 0

    import math
    if loss < 10:
        homogeneity = 0.76 + 0.24 * (1 - loss / 10)
    elif loss < 25:
        homogeneity = 0.41 + 0.35 * (1 - (loss - 10) / 15)
    else:
        homogeneity = max(0.0, 0.41 * (1 - min(loss - 25, 75) / 75))

    def lerp_color(c1, c2, t):
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        return f"rgb({r},{g},{b})"

    strat_colors = [(31,119,180), (23,190,207), (44,160,44), (255,127,14), (214,39,40)]
    uniform_color = (42, 157, 143)

    cfd_zone_h = 60
    cfd_vessel_x, cfd_vessel_y = 60, 30
    cfd_vessel_w = 160
    n_cfd = 5
    cfd_vessel_h = cfd_zone_h * n_cfd

    zone_rects_cfd = ""
    for i in range(n_cfd):
        ry = cfd_vessel_y + i * cfd_zone_h
        color = lerp_color(strat_colors[i], uniform_color, homogeneity)
        zone_rects_cfd += (
            f'<rect x="{cfd_vessel_x}" y="{ry}" '
            f'width="{cfd_vessel_w}" height="{cfd_zone_h}" '
            f'fill="{color}" stroke="none"/>\n'
        )

    imp_cx = cfd_vessel_x + cfd_vessel_w / 2
    imp_cy = cfd_vessel_y + cfd_vessel_h - 18
    shaft_top = cfd_vessel_y + cfd_vessel_h * 0.5
    cfd_impeller = (
        f'<line x1="{imp_cx}" y1="{shaft_top}" x2="{imp_cx}" y2="{imp_cy}" stroke="#444" stroke-width="3"/>'
        f'<rect x="{imp_cx-32}" y="{imp_cy-5}" width="28" height="10" rx="3" fill="#555" transform="rotate(-10,{imp_cx-18},{imp_cy})"/>'
        f'<rect x="{imp_cx+4}" y="{imp_cy-5}" width="28" height="10" rx="3" fill="#555" transform="rotate(10,{imp_cx+18},{imp_cy})"/>'
        f'<circle cx="{imp_cx}" cy="{imp_cy}" r="6" fill="#333"/>'
    )
    baffles = (
        f'<rect x="{cfd_vessel_x}" y="{cfd_vessel_y+20}" width="8" height="{cfd_vessel_h-40}" fill="#666" opacity="0.7"/>'
        f'<rect x="{cfd_vessel_x+cfd_vessel_w-8}" y="{cfd_vessel_y+20}" width="8" height="{cfd_vessel_h-40}" fill="#666" opacity="0.7"/>'
    )
    colorbar_x = cfd_vessel_x + cfd_vessel_w + 18
    colorbar = (
        f'<defs><linearGradient id="cbar" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="rgb(214,39,40)"/>'
        f'<stop offset="50%" stop-color="rgb(255,127,14)"/>'
        f'<stop offset="100%" stop-color="rgb(31,119,180)"/>'
        f'</linearGradient></defs>'
        f'<rect x="{colorbar_x}" y="{cfd_vessel_y}" width="14" height="{cfd_vessel_h}" fill="url(#cbar)" rx="3" stroke="#aaa" stroke-width="1"/>'
        f'<text x="{colorbar_x+16}" y="{cfd_vessel_y+10}" font-size="10" fill="#333" font-family="monospace">High</text>'
        f'<text x="{colorbar_x+16}" y="{cfd_vessel_y+cfd_vessel_h}" font-size="10" fill="#333" font-family="monospace">Low</text>'
        f'<text x="{colorbar_x+16}" y="{cfd_vessel_y+cfd_vessel_h+14}" font-size="9" fill="#888" font-family="monospace">[S] g/L</text>'
    )
    _preset_label_map = {
        "lab":        "~1 L Bioreactor",
        "pilot":      "~100 L Bioreactor",
        "industrial": "500 L+ Bioreactor",
    }
    vessel_title = _preset_label_map.get(st.session_state.get("preset"), "Bioreactor")

    if loss < 10:
        mix_label = "Well mixed"
        mix_bg, mix_border, mix_text = "#d4edda", "#28a745", "#155724"
    elif loss < 25:
        mix_label = "Moderate mixing"
        mix_bg, mix_border, mix_text = "#fff3cd", "#ffc107", "#856404"
    else:
        mix_label = "Poor mixing"
        mix_bg, mix_border, mix_text = "#f8d7da", "#dc3545", "#721c24"

    svg_total_h = cfd_vessel_y + cfd_vessel_h + 16
    cfd_svg_html = (
        f'<svg width="300" height="{svg_total_h}" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><clipPath id="cfd-clip"><rect x="{cfd_vessel_x}" y="{cfd_vessel_y}" width="{cfd_vessel_w}" height="{cfd_vessel_h}" rx="6"/></clipPath></defs>'
        f'{colorbar}'
        f'<g clip-path="url(#cfd-clip)">{zone_rects_cfd}</g>'
        f'<rect x="{cfd_vessel_x}" y="{cfd_vessel_y}" width="{cfd_vessel_w}" height="{cfd_vessel_h}" fill="none" stroke="#555" stroke-width="2.5" rx="6"/>'
        f'{baffles}'
        f'{cfd_impeller}'
        f'<text x="{cfd_vessel_x + cfd_vessel_w/2}" y="{cfd_vessel_y - 12}" text-anchor="middle" font-size="12" font-weight="700" fill="#333" font-family="monospace">{vessel_title}</text>'
        f'</svg>'
    )
    mix_banner = (
        f'<div style="background:{mix_bg};border-left:5px solid {mix_border};'
        f'padding:14px 16px;border-radius:6px;margin-top:8px">'
        f'<span style="font-size:23px;font-weight:700;color:{mix_text}">{mix_label}</span>'
        f'</div>'
    )

    # ── Row 2: CFD concentration gradient (left) | yield loss (right) ────────
    col_cfd2, col_yield = st.columns([1, 1])

    with col_cfd2:
        st.subheader("CFD — Concentration Gradient")
        st.markdown(cfd_svg_html, unsafe_allow_html=True)
        st.markdown(mix_banner, unsafe_allow_html=True)

    with col_yield:
        st.subheader("Scale-up Impact — Vanillin Yield")

        # Per-zone: one line each, name + value side by side
        zone_rows = "".join(
            f'<div style="margin-bottom:8px">'
            f'<span style="font-size:22px;color:#888">{zone_names[i]}</span>'
            f'<span style="font-size:22px;font-weight:700;margin-left:10px">{zones[i]["P"][-1]:.3f} g/L</span>'
            f'</div>'
            for i in range(n_zones)
        )
        st.markdown(zone_rows, unsafe_allow_html=True)

        st.markdown("<div style='margin:10px 0'></div>", unsafe_allow_html=True)

        # Large: yield loss banner with background color preserved
        if loss < 10:
            bg, border, text_color = "#d4edda", "#28a745", "#155724"
            msg = f"Yield loss: {loss:.1f}% — good mixing, zones nearly uniform."
        elif loss < 25:
            bg, border, text_color = "#fff3cd", "#ffc107", "#856404"
            msg = f"Yield loss: {loss:.1f}% — moderate heterogeneity. Scale-up risk present."
        else:
            bg, border, text_color = "#f8d7da", "#dc3545", "#721c24"
            msg = f"Yield loss: {loss:.1f}% — severe heterogeneity. Significant vanillin loss at scale."

        st.markdown(
            f'<div style="background:{bg};border-left:5px solid {border};'
            f'padding:14px 16px;border-radius:6px;margin-top:4px">'
            f'<span style="font-size:23px;font-weight:700;color:{text_color}">{msg}</span>'
            f'</div>',
            unsafe_allow_html=True
        )


    col_chart, col_hpc = st.columns([1, 1])

    with col_chart:
        st.subheader("Vanillin Production per Zone")
        fig = go.Figure()
        for i, zone in enumerate(zones):
            fig.add_trace(go.Scatter(
                x=t, y=zone['P'],
                name=zone_names[i],
                line=dict(color=zone_colors_hex[i], width=2.5)
            ))
        fig.update_layout(
            xaxis_title="Time (hr)",
            yaxis_title="Vanillin (g/L)",
            legend=dict(font=dict(size=19), title=dict(text="Zone", font=dict(size=19))),
            xaxis=dict(title_font=dict(size=19), tickfont=dict(size=18)),
            yaxis=dict(title_font=dict(size=19), tickfont=dict(size=18)),
            margin=dict(t=20),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_hpc:
        st.subheader("CFD Simulation — High Fidelity Run")
        st.info("High-fidelity CFD simulation resolves spatial velocity fields, shear stress, and concentration gradients — capturing mixing phenomena that the zone model approximates.")
        st.markdown(
            '<div style="background:#f0f2f6;border-left:5px solid #888;'
            'padding:12px 16px;border-radius:6px;margin-bottom:12px">'
            '<span style="font-size:15px;font-weight:700;color:#444">⏱ Estimated compute time</span><br>'
            '<span style="font-size:26px;font-weight:800;color:#222">4 – 8 hours</span><br>'
            '<span style="font-size:13px;color:#666">HPC cluster · 32 cores · 100 L vessel</span>'
            '</div>',
            unsafe_allow_html=True
        )
        if st.button("▶  Run CFD Simulation", use_container_width=True):
            st.session_state.cfd_running = True

        if st.session_state.get("cfd_running"):
            import time
            bar = st.progress(0, text="Initialising mesh...")
            for pct, label in [
                (15,  "Setting boundary conditions..."),
                (35,  "Solving Navier-Stokes equations..."),
                (60,  "Computing species transport..."),
                (85,  "Post-processing fields..."),
                (100, "Done."),
            ]:
                time.sleep(0.55)
                bar.progress(pct, text=label)
            st.session_state.cfd_running = False
            st.session_state.cfd_done = True
            st.success("CFD run complete — results queued for HPC cluster output.")
            time.sleep(3)
            st.rerun()
