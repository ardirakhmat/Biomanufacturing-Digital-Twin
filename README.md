# 🧫 Bioreactor Digital Twin
### Vanillin Production from *E. coli* — Ferulic Acid Bioconversion

A physics-based bioprocess simulation built as an interactive web app, demonstrating the use of **digital twin methodology** to model and predict bioreactor performance — from lab bench to industrial scale.

> Built as part of the NUS MSc Venture Creation GRIP program, exploring commercial applications of bioprocess digital twins in the biomanufacturing industry.

---

## 🔬 What It Does

This app simulates the microbial conversion of ferulic acid into vanillin by engineered *E. coli*, using **Monod kinetics** integrated over time via a stiff ODE solver. It offers two complementary simulation modes:

### 1. Ideal Reactor (Perfect Mixing)
Models a single well-mixed CSTR (Continuous Stirred Tank Reactor) — the standard assumption at lab scale. Tracks biomass growth, substrate depletion, and product formation in real time.

### 2. Scale-up: Zone Model (CFD Surrogate)
Divides the bioreactor into spatial zones (top → impeller) with inter-zone substrate exchange, approximating the **mixing heterogeneity** that emerges as vessels scale up. This is where digital twins add real value: predicting yield losses *before* you build the tank.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend / App | [Streamlit](https://streamlit.io/) |
| Numerical Integration | [SciPy](https://scipy.org/) — `solve_ivp` with Radau solver |
| Visualisation | [Plotly](https://plotly.com/python/) |
| Kinetic Model | Monod growth kinetics (CSTR-in-series surrogate) |

---

## ⚙️ Model Overview

**Monod growth kinetics:**

$$\mu = \mu_{max} \cdot \frac{S}{K_s + S}$$

**Coupled ODEs (per zone):**

$$\frac{dX}{dt} = \mu X$$

$$\frac{dS}{dt} = -\frac{\mu}{Y_{XS}} X + \alpha (S_{adj} - S)$$

$$\frac{dP}{dt} = Y_{PS} \cdot \left(-\frac{dS}{dt}\right)$$

Where:
- `X` — biomass concentration (g/L)
- `S` — ferulic acid (substrate) concentration (g/L)
- `P` — vanillin (product) concentration (g/L)
- `α` — inter-zone exchange rate (mixing intensity proxy)
- `Y_XS`, `Y_PS` — biomass and product yield coefficients

Default parameters are grounded in published literature (Yeoh et al., 2021).

---

## 🚀 Running Locally

```bash
# 1. Clone the repo
git clone https://github.com/your-username/bioreactor-digital-twin.git
cd bioreactor-digital-twin

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## 🎛 Parameters You Can Tune

| Parameter | Symbol | Default | Description |
|---|---|---|---|
| Max growth rate | µmax | 0.15 /hr | Ceiling growth rate under saturating substrate |
| Saturation constant | Ks | 0.05 g/L | Substrate concentration at half max growth |
| Biomass yield | Yxs | 0.4 g/g | Biomass produced per gram of ferulic acid consumed |
| Vanillin yield | Yps | 0.7 g/g | Vanillin produced per gram of ferulic acid consumed |
| Initial biomass | X0 | 0.05 g/L | Inoculum concentration |
| Initial substrate | S0 | 1.1 g/L | Starting ferulic acid concentration |
| Simulation time | t_end | 20 hr | Duration of the bioprocess |
| Number of zones | n | 3 | Spatial discretisation (Zone Model only) |
| Mixing intensity | α | 0.1 | Inter-zone exchange rate (Zone Model only) |

---

## 📊 Scale-up Presets

The Zone Model includes three one-click scenarios:

| Preset | Scale | Exchange Rate | Behaviour |
|---|---|---|---|
| Lab scale | ~1 L | 2.0 | Near-perfect mixing, uniform zones |
| Pilot scale | ~100 L | 0.3 | Moderate heterogeneity, some yield loss |
| Industrial scale | 500 L+ | 0.02 | Severe gradients, significant vanillin loss |

---

## 💡 Why This Matters

Scaling bioprocesses from lab to industrial volume is notoriously unpredictable. Mixing time increases non-linearly with vessel size, creating **substrate gradients** that starve cells in low-mixing zones. A digital twin that captures this behaviour can:

- **Reduce costly trial batches** at pilot and industrial scale
- **Optimise impeller configuration and feed strategies** in silico
- **Support process validation** for regulated biomanufacturing environments (GMP, FDA PAT)

This prototype demonstrates the core simulation logic. A production-grade system would integrate real sensor data (DoE-calibrated parameters, online substrate probes) for closed-loop prediction.

---

## 📁 Project Structure

```
bioreactor-digital-twin/
├── app.py              # Streamlit UI, mode selection, parameter controls
├── model.py            # Kinetic model, ODE definitions, simulation runners
├── requirements.txt    # Python dependencies
└── README.md
```

---

## 📚 References

- Yeoh, J.W. *et al.* (2021). Vanillin production from ferulic acid using engineered *E. coli*. *Bioresource Technology*.
- Monod, J. (1949). The growth of bacterial cultures. *Annual Review of Microbiology*.
- Noorman, H. (2011). An industrial perspective on bioreactor scale-down. *Biotechnology Journal*.

---

## 👤 Author

**Ardi** — MSc Venture Creation, National University of Singapore  
Mechanical Engineering background · iOS · Go · Bioprocess  

*Built for the NUS GRIP Program, 2025–2026.*
