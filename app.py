import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import numpy as np
from model import run_simulation, run_zone_simulation

# ── Shared helpers ────────────────────────────────────────────────────────────
def lerp_color(c1, c2, t):
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return f"rgb({r},{g},{b})"

# Stratified zone colors (bottom→top): red, orange, green, light-blue, dark-blue
STRAT_COLORS = [(214,39,40), (255,127,14), (44,160,44), (23,190,207), (31,119,180)]
UNIFORM_COLOR = (42, 157, 143)

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

# ── Kinetic parameters: only shown in Ideal Reactor mode ─────────────────────
if mode == "Ideal Reactor (Perfect Mixing)":
    st.sidebar.header("Kinetic Parameters")
    mu_max = st.sidebar.slider("Max growth rate µmax (1/hr)", 0.05, 0.5, 0.15, 0.01)
    ks = st.sidebar.slider("Saturation constant Ks (g/L)", 0.01, 0.5, 0.05, 0.01)
    yxs = st.sidebar.slider("Biomass yield Yxs (g/g)", 0.1, 0.8, 0.4, 0.05)
    yps = st.sidebar.slider("Vanillin yield Yps (g/g)", 0.1, 1.0, 0.7, 0.05)
    X0 = st.sidebar.slider("Initial biomass X0 (g/L)", 0.01, 0.2, 0.05, 0.01)
    S0 = st.sidebar.slider("Initial ferulic acid S0 (g/L)", 0.5, 3.0, 1.1, 0.1)
    t_end = st.sidebar.slider("Simulation time (hr)", 5.0, 40.0, 20.0, 1.0)
else:
    # Fixed kinetic defaults used by Scale-up mode
    mu_max, ks, yxs, yps = 0.15, 0.05, 0.4, 0.7
    X0, S0, t_end = 0.05, 1.1, 20.0

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
    n_zones = 5  # Fixed at 5 zones

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


    if loss < 10:
        mix_label = "Well mixed"
        mix_bg, mix_border, mix_text = "#d4edda", "#28a745", "#155724"
    elif loss < 25:
        mix_label = "Moderate mixing"
        mix_bg, mix_border, mix_text = "#fff3cd", "#ffc107", "#856404"
    else:
        mix_label = "Poor mixing"
        mix_bg, mix_border, mix_text = "#f8d7da", "#dc3545", "#721c24"

    mix_banner = (
        f'<div style="background:{mix_bg};border-left:5px solid {mix_border};'
        f'padding:14px 16px;border-radius:6px;margin-top:8px">'
        f'<span style="font-size:23px;font-weight:700;color:{mix_text}">{mix_label}</span>'
        f'</div>'
    )

    # ── Shared zone colors (used by both 3D bioreactor and line chart) ────────
    # Zone 1 (top, z=8-10) = worst mixing = STRAT_COLORS[0]
    # Zone 5 (bottom, z=0-2) = impeller, best mixing = STRAT_COLORS[4]
    # bio3d_zone_colors[0] = bottom band (z=0-2) = Zone 5 color
    # bio3d_zone_colors[4] = top band   (z=8-10) = Zone 1 color
    bio3d_zone_colors = [
        lerp_color(STRAT_COLORS[4 - i], UNIFORM_COLOR, homogeneity)
        for i in range(5)
    ]

    # ── Row 2: CFD concentration gradient (left) | vanillin chart (right) ────
    col_cfd2, col_yield = st.columns([1, 1])

    with col_cfd2:
        st.subheader("3D Bioreactor Zone Model")

        # ── 3D bioreactor geometry ────────────────────────────────────────────
        b_height, b_radius = 10, 2.2
        theta = np.linspace(0, 2 * np.pi, 50)
        z_vals = np.linspace(0, b_height, 50)
        theta_grid, z_grid = np.meshgrid(theta, z_vals)
        x_grid = b_radius * np.cos(theta_grid)
        y_grid = b_radius * np.sin(theta_grid)

        r2 = np.linspace(0, b_radius, 40)
        theta2 = np.linspace(0, 2 * np.pi, 50)
        r_grid, theta2_grid = np.meshgrid(r2, theta2)
        x_cap = r_grid * np.cos(theta2_grid)
        y_cap = r_grid * np.sin(theta2_grid)

        blade_len, blade_z = 1.45, 0.75
        shaft_bottom, shaft_top_z = 0.55, 8.9

        bio_zones = [
            (bio3d_zone_colors[0], 0, 2),
            (bio3d_zone_colors[1], 2, 4),
            (bio3d_zone_colors[2], 4, 6),
            (bio3d_zone_colors[3], 6, 8),
            (bio3d_zone_colors[4], 8, 10),
        ]

        def make_bio3d_traces(rotation_deg):
            traces = []
            for color, z_min, z_max in bio_zones:
                z_layer = np.where(
                    (z_grid >= z_min) & (z_grid <= z_max), z_grid, np.nan
                )
                traces.append(go.Surface(
                    x=x_grid, y=y_grid, z=z_layer,
                    surfacecolor=np.ones_like(z_grid),
                    colorscale=[[0, color], [1, color]],
                    showscale=False, opacity=0.82, hoverinfo="skip"
                ))
            # Bottom cap
            traces.append(go.Surface(
                x=x_cap, y=y_cap, z=np.zeros_like(x_cap),
                surfacecolor=np.ones_like(x_cap),
                colorscale=[[0, bio3d_zone_colors[0]], [1, bio3d_zone_colors[0]]],
                showscale=False, opacity=0.95, hoverinfo="skip"
            ))
            # Top cap
            traces.append(go.Surface(
                x=x_cap, y=y_cap, z=np.full_like(x_cap, b_height),
                surfacecolor=np.ones_like(x_cap),
                colorscale=[[0, bio3d_zone_colors[4]], [1, bio3d_zone_colors[4]]],
                showscale=False, opacity=0.95, hoverinfo="skip"
            ))
            # Shaft
            traces.append(go.Scatter3d(
                x=[0, 0], y=[0, 0], z=[shaft_bottom, shaft_top_z],
                mode="lines", line=dict(color="rgb(55,55,55)", width=14),
                showlegend=False, hoverinfo="skip"
            ))
            # Hub
            traces.append(go.Scatter3d(
                x=[0], y=[0], z=[blade_z], mode="markers",
                marker=dict(size=9, color="rgb(65,65,65)"),
                showlegend=False, hoverinfo="skip"
            ))
            # Spinning impeller blades
            for angle in np.array([0, 120, 240]) + rotation_deg:
                rad = np.deg2rad(angle)
                x1 = blade_len * np.cos(rad)
                y1 = blade_len * np.sin(rad)
                traces.append(go.Scatter3d(
                    x=[0, x1], y=[0, y1], z=[blade_z, blade_z],
                    mode="lines", line=dict(color="rgb(75,75,75)", width=18),
                    showlegend=False, hoverinfo="skip"
                ))
                perp = rad + np.pi / 2
                tip = 0.24
                traces.append(go.Scatter3d(
                    x=[x1 + tip*np.cos(perp), x1 - tip*np.cos(perp)],
                    y=[y1 + tip*np.sin(perp), y1 - tip*np.sin(perp)],
                    z=[blade_z, blade_z],
                    mode="lines", line=dict(color="rgb(75,75,75)", width=14),
                    showlegend=False, hoverinfo="skip"
                ))
            # Outline rings
            for z_ring in [0, b_height]:
                traces.append(go.Scatter3d(
                    x=b_radius * np.cos(theta),
                    y=b_radius * np.sin(theta),
                    z=np.full_like(theta, z_ring),
                    mode="lines", line=dict(color="rgb(90,90,90)", width=4),
                    showlegend=False, hoverinfo="skip"
                ))
            return traces

        bio3d_fig = go.Figure(data=make_bio3d_traces(0))
        bio3d_fig.frames = [
            go.Frame(data=make_bio3d_traces(rot), name=str(rot))
            for rot in range(0, 360, 12)
        ]
        bio3d_fig.update_layout(
            width=420, height=500,
            margin=dict(l=0, r=0, t=20, b=0),
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
                aspectmode="manual",
                aspectratio=dict(x=1, y=1, z=2.25),
                camera=dict(eye=dict(x=1.8, y=1.55, z=1.45)),
                bgcolor="white",
            ),
        )

        plot_html = bio3d_fig.to_html(
            include_plotlyjs="cdn", full_html=False, div_id="bioreactor3d"
        )

        combined_html = f"""
        <div style="position:relative;width:420px;height:520px">
          {plot_html}
        </div>
        <script>
        document.addEventListener("DOMContentLoaded", function() {{
            const gd = document.getElementById("bioreactor3d");
            if (gd) {{
                Plotly.animate(gd, null, {{
                    frame: {{duration: 80, redraw: true}},
                    transition: {{duration: 0}},
                    mode: "immediate",
                    fromcurrent: true
                }});
            }}
        }});
        </script>
        """

        components.html(combined_html, height=530, scrolling=False)

    with col_yield:
        st.subheader("Vanillin Production per Zone")
        fig = go.Figure()
        for i, zone in enumerate(zones):
            fig.add_trace(go.Scatter(
                x=t, y=zone['P'],
                name=zone_names[i],
                line=dict(color=bio3d_zone_colors[n_zones - 1 - i], width=2.5)
            ))
        fig.update_layout(
            xaxis_title="Time (hr)",
            yaxis_title="Vanillin (g/L)",
            legend=dict(
                orientation="h",
                yanchor="top", y=-0.22,
                xanchor="center", x=0.5,
                font=dict(size=16),
                title=dict(text="Zone", font=dict(size=16)),
            ),
            xaxis=dict(title_font=dict(size=19), tickfont=dict(size=18)),
            yaxis=dict(title_font=dict(size=19), tickfont=dict(size=18)),
            margin=dict(t=80, b=100),
            height=530,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2b: banners side by side ─────────────────────────────────────────
    col_mix_banner, col_yield_banner = st.columns([1, 1])

    with col_mix_banner:
        st.markdown(mix_banner, unsafe_allow_html=True)

    with col_yield_banner:
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
            f'padding:14px 16px;border-radius:6px">'
            f'<span style="font-size:23px;font-weight:700;color:{text_color}">{msg}</span>'
            f'</div>',
            unsafe_allow_html=True
        )


    col_chart, col_hpc = st.columns([1, 1])

    with col_chart:
        st.subheader("Vanillin Yield")

        # Per-zone: one line each, name + value side by side
        zone_rows = "".join(
            f'<div style="margin-bottom:8px">'
            f'<span style="font-size:22px;color:#888">{zone_names[i]}</span>'
            f'<span style="font-size:22px;font-weight:700;margin-left:10px">{zones[i]["P"][-1]:.3f} g/L</span>'
            f'</div>'
            for i in range(n_zones)
        )
        st.markdown(zone_rows, unsafe_allow_html=True)

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
