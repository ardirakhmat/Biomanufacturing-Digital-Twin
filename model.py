import numpy as np
from scipy.integrate import solve_ivp

# E. coli parameters - ferulic acid to vanillin
# Based on Yeoh et al. (2021) and literature values
MU_MAX = 0.15     # maximum specific growth rate (1/hr) - slower for this pathway
KS = 0.05         # Monod saturation constant for ferulic acid (g/L)
YXS = 0.4         # biomass yield on ferulic acid (g biomass / g substrate)
YPS = 0.7         # vanillin yield on ferulic acid (g vanillin / g substrate)

def monod_growth_rate(mu_max, ks, S):
    S = max(S, 0)
    return mu_max * S / (ks + S)

def bioreactor_odes(t, y, mu_max, ks, yxs, yps):
    X, S, P = y
    S = max(S, 0)
    X = max(X, 0)
    mu = monod_growth_rate(mu_max, ks, S)
    dXdt = mu * X
    dSdt = -(mu / yxs) * X
    dPdt = yps * (-dSdt)   # vanillin produced proportional to substrate consumed
    return [dXdt, dSdt, dPdt]

def run_simulation(mu_max=MU_MAX, ks=KS, yxs=YXS, yps=YPS,
                   X0=0.05, S0=1.1, t_end=20.0):
    sol = solve_ivp(
        bioreactor_odes,
        t_span=(0, t_end),
        y0=[X0, S0, 0.0],
        args=(mu_max, ks, yxs, yps),
        method='Radau',
        dense_output=True
    )
    t = np.linspace(0, t_end, 200)
    y = sol.sol(t)
    return t, y[0], y[1], y[2]  # time, biomass, substrate, vanillin

def cstr_zones_odes(t, y, mu_max, ks, yxs, yps, n_zones, exchange_rate):
    # y = [X1, S1, P1, X2, S2, P2, ...]
    dydt = []
    for i in range(n_zones):
        X = max(y[3*i], 0)
        S = max(y[3*i + 1], 0)
        P = max(y[3*i + 2], 0)
        mu = monod_growth_rate(mu_max, ks, S)

        dXdt = mu * X
        dSdt = -(mu / yxs) * X
        dPdt = yps * (-dSdt)

        # exchange substrate with neighbours
        if i > 0:
            S_prev = max(y[3*(i-1) + 1], 0)
            dSdt += exchange_rate * (S_prev - S)
        if i < n_zones - 1:
            S_next = max(y[3*(i+1) + 1], 0)
            dSdt += exchange_rate * (S_next - S)

        dydt.extend([dXdt, dSdt, dPdt])
    return dydt

def run_zone_simulation(mu_max=MU_MAX, ks=KS, yxs=YXS, yps=YPS,
                        X0=0.05, S0=1.1, n_zones=3, exchange_rate=0.1, t_end=20.0):
    # Ferulic acid gradient: low at top, high near impeller.
    # Weights sum to 1, scaled so total substrate = S0 * n_zones
    # (each zone holds the same volume, average concentration = S0).
    weights = np.linspace(0.3, 1.0, n_zones)
    weights = weights / weights.sum()          # normalise → sum to 1
    S_init = weights * S0 * n_zones            # each zone's concentration; mean = S0

    y0 = []
    for i in range(n_zones):
        y0.extend([X0, S_init[i], 0.0])

    sol = solve_ivp(
        cstr_zones_odes,
        t_span=(0, t_end),
        y0=y0,
        args=(mu_max, ks, yxs, yps, n_zones, exchange_rate),
        method='Radau',
        dense_output=True
    )
    t = np.linspace(0, t_end, 200)
    y = sol.sol(t)

    zones = []
    for i in range(n_zones):
        zones.append({
            'X': y[3*i],
            'S': y[3*i + 1],
            'P': y[3*i + 2]
        })
    return t, zones
