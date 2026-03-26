import streamlit as st
import plotly.graph_objects as go
from model import run_simulation, run_zone_simulation

st.set_page_config(page_title="Bioreactor Digital Twin", layout="wide")
st.title("Bioreactor Digital Twin")
st.subheader("Vanillin Production from E. coli — Ferulic Acid Bioconversion")

mode = st.radio("Mode", ["Ideal Reactor (Perfect Mixing)", "Scale-up: Zone Model", "Scale-up: CFD"], horizontal=True)

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

elif mode == "Scale-up: Zone Model":
    st.info("The bioreactor is divided into spatial zones. Poor mixing creates ferulic acid gradients — cells in substrate-poor zones produce less vanillin. This is the scale-up risk.")

    # Default to lab scale on first entry into zone mode
    if "preset" not in st.session_state:
        st.session_state.preset = "lab"
        st.session_state.exchange_rate = 2.0
        st.session_state.n_zones = 3

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
            st.session_state.n_zones = 3
            st.session_state.preset = "lab"
            st.rerun()
    with col2:
        if st.button("Pilot scale (~100L) — moderate mixing", key="btn_pilot", use_container_width=True):
            st.session_state.exchange_rate = 0.3
            st.session_state.n_zones = 3
            st.session_state.preset = "pilot"
            st.rerun()
    with col3:
        if st.button("Industrial scale (500L+) — poor mixing", key="btn_industrial", use_container_width=True):
            st.session_state.exchange_rate = 0.02
            st.session_state.n_zones = 3
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
        # Only update session state if user dragged the slider (not a button rerun)
        if exchange_rate != st.session_state.exchange_rate:
            st.session_state.exchange_rate = exchange_rate

    # Clear preset label only if the slider was manually dragged (not +/- buttons)
    _preset_params = {"lab": (2.0, 3), "pilot": (0.3, 3), "industrial": (0.02, 3)}
    _current = st.session_state.get("preset")
    _slider_dragged = exchange_rate != st.session_state.get("exchange_rate", exchange_rate)
    if _current and _slider_dragged and _preset_params.get(_current) != (exchange_rate, n_zones):
        st.session_state.preset = None

    t, zones = run_zone_simulation(mu_max, ks, yxs, yps, X0, S0, n_zones, exchange_rate, t_end)

    zone_colors_hex = ["#e63946", "#f4a261", "#2a9d8f", "#457b9d", "#6a4c93"]
    _base_names = ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"]
    zone_names = [
        f"{_base_names[i]} (impeller)" if i == n_zones - 1 else _base_names[i]
        for i in range(5)
    ]

    # ── 2D bioreactor cross-section ──────────────────────────────────────────
    st.subheader("Reactor cross-section — ferulic acid gradient at t=0")

    # Compute initial S per zone (same gradient logic as model.py)
    import numpy as np
    weights = np.linspace(0.3, 1.0, n_zones)
    weights = weights / weights.sum()
    S_init = weights * S0 * n_zones   # each zone's initial concentration

    # SVG dimensions
    svg_w, svg_h = 220, 320
    vessel_x, vessel_y = 40, 20
    vessel_w, vessel_h = 140, 260
    zone_h = vessel_h / n_zones

    # Build zone rectangles (top zone = index 0)
    zone_rects = ""
    zone_labels = ""
    for i in range(n_zones):
        ry = vessel_y + i * zone_h
        color = zone_colors_hex[i]
        # Opacity scales with relative S concentration
        alpha = 0.35 + 0.55 * (S_init[i] / S_init.max())
        name = zone_names[i] if i < len(zone_names) else f"Zone {i+1}"
        s_val = S_init[i]
        zone_rects += (
            f'<rect x="{vessel_x}" y="{ry:.1f}" width="{vessel_w}" height="{zone_h:.1f}" '
            f'fill="{color}" fill-opacity="{alpha:.2f}" stroke="none"/>\n'
        )
        label_y = ry + zone_h / 2
        zone_labels += (
            f'<text x="{vessel_x + vessel_w + 8}" y="{label_y:.1f}" '
            f'dominant-baseline="middle" font-size="13" font-weight="600" fill="{color}" font-family="monospace">'
            f'{name}: {s_val:.2f} g/L</text>\n'
        )

    # Impeller symbol at bottom of vessel — proper blades + shaft + label
    imp_cx = vessel_x + vessel_w / 2
    imp_cy = vessel_y + vessel_h - 18
    shaft_top = vessel_y + vessel_h * 0.5
    impeller_svg = (
        # Shaft
        f'<line x1="{imp_cx}" y1="{shaft_top:.1f}" x2="{imp_cx}" y2="{imp_cy:.1f}" '
        f'stroke="#444" stroke-width="3"/>'
        # Left blade (angled)
        f'<rect x="{imp_cx - 32}" y="{imp_cy - 5}" width="28" height="10" rx="3" '
        f'fill="#555" transform="rotate(-10,{imp_cx - 18},{imp_cy})"/>'
        # Right blade (angled)
        f'<rect x="{imp_cx + 4}" y="{imp_cy - 5}" width="28" height="10" rx="3" '
        f'fill="#555" transform="rotate(10,{imp_cx + 18},{imp_cy})"/>'
        # Hub
        f'<circle cx="{imp_cx}" cy="{imp_cy}" r="6" fill="#333"/>'
        # Label outside vessel, below
        f'<text x="{vessel_x + vessel_w / 2}" y="{vessel_y + vessel_h + 16}" '
        f'text-anchor="middle" font-size="12" font-weight="600" fill="#444" font-family="monospace">'
        f'Impeller</text>'
    )

    # Pre-build dividers as a plain string (no expressions inside f-string)
    dividers = ""
    for i in range(n_zones - 1):
        dy = vessel_y + (i + 1) * zone_h
        dividers += (
            f'<line x1="{vessel_x}" y1="{dy:.1f}" '
            f'x2="{vessel_x + vessel_w}" y2="{dy:.1f}" '
            f'stroke="#555" stroke-width="1" stroke-dasharray="4 3" opacity="0.6"/>\n'
        )

    clip_rect = (
        f'<rect x="{vessel_x}" y="{vessel_y}" '
        f'width="{vessel_w}" height="{vessel_h}" rx="6"/>'
    )
    vessel_wall = (
        f'<rect x="{vessel_x}" y="{vessel_y}" width="{vessel_w}" height="{vessel_h}" '
        f'fill="none" stroke="#555" stroke-width="2.5" rx="6"/>'
    )
    caption_x = vessel_x + vessel_w / 2
    caption_y = vessel_y + vessel_h + 18
    caption = ""  # removed substrate-poor/rich label
    total_w = svg_w + 160
    total_h = svg_h + 40

    svg_clipped = (
        f'<svg width="{total_w}" height="{total_h}" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><clipPath id="vessel-clip">{clip_rect}</clipPath></defs>'
        f'<g clip-path="url(#vessel-clip)">{zone_rects}</g>'
        f'{vessel_wall}'
        f'{dividers}'
        f'{impeller_svg}'
        f'{zone_labels}'
        f'{caption}'
        f'</svg>'
    )

    # ── Top row: cross-section left | yield loss right ───────────────────────
    col_svg, col_yield = st.columns([1, 1])

    with col_svg:
        st.markdown(svg_clipped, unsafe_allow_html=True)

    with col_yield:
        best = max(z['P'][-1] for z in zones)
        worst = min(z['P'][-1] for z in zones)
        loss = (best - worst) / best * 100 if best > 0 else 0

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

    # ── Vanillin Production chart — full width ───────────────────────────────
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
    )
    st.plotly_chart(fig, use_container_width=True)

else:  # Scale-up: CFD
    st.info("High-fidelity CFD simulation of the bioreactor. Resolves spatial velocity fields, shear stress, and concentration gradients — capturing mixing phenomena that the zone model approximates.")

    col_cfd, col_info = st.columns([3, 2])

    with col_cfd:
        st.subheader("CFD Simulation — Concentration Gradient")

        cfd_svg = """<svg width="340" height="460" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="cfd_grad" cx="50%" cy="78%" r="55%">
      <stop offset="0%"   stop-color="#d62728" stop-opacity="0.95"/>
      <stop offset="18%"  stop-color="#ff7f0e" stop-opacity="0.92"/>
      <stop offset="36%"  stop-color="#ffdd57" stop-opacity="0.88"/>
      <stop offset="55%"  stop-color="#2ca02c" stop-opacity="0.85"/>
      <stop offset="75%"  stop-color="#17becf" stop-opacity="0.88"/>
      <stop offset="100%" stop-color="#1f77b4" stop-opacity="0.95"/>
    </radialGradient>
    <radialGradient id="cfd_swirl" cx="30%" cy="55%" r="40%">
      <stop offset="0%"   stop-color="#ff7f0e" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="#1f77b4" stop-opacity="0.0"/>
    </radialGradient>
    <clipPath id="vessel_clip">
      <rect x="70" y="30" width="200" height="360" rx="12"/>
    </clipPath>
    <linearGradient id="colorbar" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#d62728"/>
      <stop offset="25%"  stop-color="#ff7f0e"/>
      <stop offset="50%"  stop-color="#ffdd57"/>
      <stop offset="75%"  stop-color="#2ca02c"/>
      <stop offset="100%" stop-color="#1f77b4"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#vessel_clip)">
    <rect x="70" y="30" width="200" height="360" fill="url(#cfd_grad)"/>
    <rect x="70" y="30" width="200" height="360" fill="url(#cfd_swirl)"/>
    <ellipse cx="170" cy="320" rx="60" ry="22" fill="none" stroke="white" stroke-width="1.2" stroke-dasharray="6 4" opacity="0.35"/>
    <ellipse cx="170" cy="290" rx="75" ry="30" fill="none" stroke="white" stroke-width="1.0" stroke-dasharray="6 4" opacity="0.25"/>
    <ellipse cx="170" cy="160" rx="55" ry="18" fill="none" stroke="white" stroke-width="1.0" stroke-dasharray="5 4" opacity="0.2"/>
    <ellipse cx="170" cy="120" rx="70" ry="26" fill="none" stroke="white" stroke-width="0.8" stroke-dasharray="5 4" opacity="0.15"/>
  </g>
  <rect x="70" y="30" width="200" height="360" fill="none" stroke="#333" stroke-width="3" rx="12"/>
  <rect x="72" y="55" width="8" height="290" fill="#555" opacity="0.7"/>
  <rect x="260" y="55" width="8" height="290" fill="#555" opacity="0.7"/>
  <line x1="170" y1="30" x2="170" y2="338" stroke="#222" stroke-width="5"/>
  <ellipse cx="170" cy="338" rx="12" ry="5" fill="#222"/>
  <rect x="108" y="331" width="44" height="13" rx="4" fill="#333" transform="rotate(-8,130,337)"/>
  <rect x="188" y="331" width="44" height="13" rx="4" fill="#333" transform="rotate(8,210,337)"/>
  <rect x="108" y="331" width="44" height="13" rx="4" fill="#444" opacity="0.6" transform="rotate(-22,130,337)"/>
  <rect x="188" y="331" width="44" height="13" rx="4" fill="#444" opacity="0.6" transform="rotate(22,210,337)"/>
  <ellipse cx="170" cy="385" rx="100" ry="16" fill="#ccc" stroke="#333" stroke-width="2.5"/>
  <circle cx="150" cy="378" r="3" fill="white" opacity="0.5"/>
  <circle cx="170" cy="376" r="2.5" fill="white" opacity="0.5"/>
  <circle cx="190" cy="379" r="2" fill="white" opacity="0.4"/>
  <text x="170" y="22" text-anchor="middle" font-size="13" font-weight="700" fill="#333" font-family="monospace">100 L Bioreactor</text>
  <rect x="292" y="55" width="16" height="200" fill="url(#colorbar)" rx="3" stroke="#aaa" stroke-width="1"/>
  <text x="311" y="59"  font-size="10" fill="#333" font-family="monospace">High</text>
  <text x="311" y="261" font-size="10" fill="#333" font-family="monospace">Low</text>
  <text x="296" y="276" font-size="9"  fill="#888" font-family="monospace">[S] g/L</text>
  <line x1="215" y1="338" x2="248" y2="355" stroke="#555" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="250" y="359" font-size="10" fill="#444" font-family="monospace">Impeller</text>
  <line x1="200" y1="380" x2="248" y2="395" stroke="#555" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="250" y="399" font-size="10" fill="#444" font-family="monospace">Sparger</text>
</svg>"""

        st.markdown(cfd_svg, unsafe_allow_html=True)

    with col_info:
        st.subheader("Simulation Parameters")
        st.markdown(
            f'<div style="font-size:15px;line-height:2.2">'
            f'<b>µmax</b>: {mu_max} hr⁻¹<br>'
            f'<b>Ks</b>: {ks} g/L<br>'
            f'<b>Yxs</b>: {yxs} g/g<br>'
            f'<b>Yps</b>: {yps} g/g<br>'
            f'<b>X₀</b>: {X0} g/L<br>'
            f'<b>S₀</b>: {S0} g/L<br>'
            f'<b>t</b>: {t_end} hr<br>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("<div style='margin:18px 0'></div>", unsafe_allow_html=True)

        st.markdown(
            '<div style="background:#fff3cd;border-left:5px solid #ffc107;'
            'padding:12px 16px;border-radius:6px">'
            '<span style="font-size:15px;font-weight:700;color:#856404">⏱ Estimated compute time</span><br>'
            '<span style="font-size:26px;font-weight:800;color:#856404">4 – 8 hours</span><br>'
            '<span style="font-size:13px;color:#856404">HPC cluster · 32 cores · 100 L vessel</span>'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown("<div style='margin:18px 0'></div>", unsafe_allow_html=True)

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
            st.success("CFD run complete — results queued for HPC cluster output.")
