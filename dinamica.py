#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
ANÁLISE DE ESTABILIDADE DINÂMICA — Caça Canard-Delta (UFU / Projeto II)
=============================================================================
Modos calculados:
  Longitudinal  → Short Period, Phugoid
  Lateral-Dir.  → Dutch Roll, Roll Subsidence, Espiral
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import linalg
import pandas as pd
from pathlib import Path

plt.rcParams.update({
    'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3,
    'figure.figsize': (10, 6), 'figure.dpi': 150,
    'savefig.dpi': 200,
})

# ======================== DADOS DA AERONAVE ================================
ALT_FT = 30_000; ALT_M = ALT_FT * 0.3048; MACH = 0.85; g = 9.80665
T_ISA = 288.15 - 0.0065 * ALT_M
rho = 1.225 * (T_ISA / 288.15) ** 4.2559
a_sound = np.sqrt(1.4 * 287.058 * T_ISA)
U0 = MACH * a_sound
q_bar = 0.5 * rho * U0**2

S_ref = 32.420; c_ref = 2.76; b_ref = 11.72
m_mid = 0.80 * 30442; W0 = m_mid * g

# *** MOMENTOS DE INÉRCIA — SUBSTITUIR COM VALORES DO SOLIDWORKS ***
Ixx = 40000; Iyy = 230000; Izz = 260000; Ixz = 4000

# ======================== DERIVADAS AVL (alfa=4 deg, cruzeiro) ==============
CL0 = 0.27256; CD0_val = 0.02676; Cm0 = -0.00060

CL_alpha = 3.876101; CD_alpha = 2*0.00565*CL0*CL_alpha; Cm_alpha = -0.007875
CL_q = 5.985502; Cm_q = -6.151259         # AVL st_alpha_+04.00
CL_alpha_dot = 1.0; Cm_alpha_dot = -1.0   # estimativas (canard — VLM não fornece)
CD_u = 0.0; CL_u = 0.0; Cm_u = 0.0

CY_beta = -0.317028; Cl_beta = -0.074704; Cn_beta = 0.056287   # AVL
CY_p = 0.022756;  Cl_p = -0.312634; Cn_p = -0.014293           # AVL
CY_r = 0.156048;  Cl_r = 0.078801;  Cn_r = -0.032952           # AVL

# ======================== DERIVADAS DIMENSIONAIS ===========================
print("=" * 70)
print("   ANÁLISE DE ESTABILIDADE DINÂMICA — CACA-UFU")
print("=" * 70)
print(f"\nCondição: {ALT_FT} ft, M={MACH}, V={U0:.1f} m/s, q={q_bar:.1f} Pa")
print(f"Massa: {m_mid:.0f} kg | Ixx={Ixx} Iyy={Iyy} Izz={Izz} Ixz={Ixz}")

Xu = -(CD_u + 2*CD0_val) * q_bar * S_ref / (m_mid * U0)
Xa = (CL0 - CD_alpha) * q_bar * S_ref / m_mid
Zu = -(CL_u + 2*CL0) * q_bar * S_ref / (m_mid * U0)
Za = -(CL_alpha + CD0_val) * q_bar * S_ref / m_mid
Zq = -CL_q * (c_ref/(2*U0)) * q_bar * S_ref / m_mid
Za_dot = -CL_alpha_dot * (c_ref/(2*U0)) * q_bar * S_ref / m_mid

Mu = Cm_u * q_bar * S_ref * c_ref / (Iyy * U0)
Ma = Cm_alpha * q_bar * S_ref * c_ref / Iyy
Mq = Cm_q * (c_ref/(2*U0)) * q_bar * S_ref * c_ref / Iyy
Ma_dot = Cm_alpha_dot * (c_ref/(2*U0)) * q_bar * S_ref * c_ref / Iyy

Gamma = Ixx * Izz - Ixz**2
c1 = Izz/Gamma; c2 = Ixz/Gamma; c3 = Ixx/Gamma

Yb = CY_beta * q_bar * S_ref / m_mid
Yp = CY_p * (b_ref/(2*U0)) * q_bar * S_ref / m_mid
Yr = CY_r * (b_ref/(2*U0)) * q_bar * S_ref / m_mid

Lb_raw = Cl_beta*q_bar*S_ref*b_ref; Nb_raw = Cn_beta*q_bar*S_ref*b_ref
Lp_raw = Cl_p*(b_ref/(2*U0))*q_bar*S_ref*b_ref; Np_raw = Cn_p*(b_ref/(2*U0))*q_bar*S_ref*b_ref
Lr_raw = Cl_r*(b_ref/(2*U0))*q_bar*S_ref*b_ref; Nr_raw = Cn_r*(b_ref/(2*U0))*q_bar*S_ref*b_ref

Lb = c1*Lb_raw + c2*Nb_raw; Lp = c1*Lp_raw + c2*Np_raw; Lr = c1*Lr_raw + c2*Nr_raw
Nb = c2*Lb_raw + c3*Nb_raw; Np = c2*Lp_raw + c3*Np_raw; Nr = c2*Lr_raw + c3*Nr_raw

# ======================== MATRIZES DE ESTADO ================================
A_long = np.array([
    [Xu,     Xa,     0,          -g],
    [Zu/U0,  Za/U0,  1 + Zq/U0,  0],
    [Mu + Ma_dot*Zu/U0, Ma + Ma_dot*Za/U0, Mq + Ma_dot*(1+Zq/U0), 0],
    [0,      0,      1,           0]
])

A_lat = np.array([
    [Yb/U0,  Yp/U0,  -(1.0 - Yr/U0),  g/U0],
    [Lb,     Lp,      Lr,               0],
    [Nb,     Np,      Nr,               0],
    [0,      1,       0,                0]
])

state_long = ['Δu', 'Δα', 'Δq', 'Δθ']
state_lat = ['Δβ', 'Δp', 'Δr', 'Δφ']

print("\nMatriz A Longitudinal:")
print(pd.DataFrame(A_long, index=state_long, columns=state_long).to_string(float_format='{:.6f}'.format))
print("\nMatriz A Latero-Direcional:")
print(pd.DataFrame(A_lat, index=state_lat, columns=state_lat).to_string(float_format='{:.6f}'.format))

# ======================== ANÁLISE DE AUTOVALORES ============================
def analyze_eigen(A, label):
    eigvals, eigvecs = linalg.eig(A)
    print(f"\n{'='*60}\n  AUTOVALORES — {label}\n{'='*60}")
    modes = []; processed = set()
    for i, ev in enumerate(eigvals):
        if i in processed: continue
        r, im = ev.real, ev.imag
        if abs(im) > 1e-8:
            wn = abs(ev); zeta = -r/wn
            wd = wn*np.sqrt(max(0, 1-zeta**2))
            T = 2*np.pi/wd if wd > 0 else np.inf
            th = np.log(2)/abs(r) if abs(r) > 0 else np.inf
            for j in range(i+1, len(eigvals)):
                if j not in processed and abs(eigvals[j]-ev.conjugate()) < 1e-6:
                    processed.add(j); break
            modes.append({'Tipo':'Oscil.','re':r,'im':abs(im),'wn':wn,'wd':wd,
                          'zeta':zeta,'T':T,'th':th,'stable':'SIM' if r<0 else 'NÃO'})
            print(f"\n  λ = {r:+.4f} ± {abs(im):.4f}j  |  ωn={wn:.4f}  ζ={zeta:.4f}  T={T:.2f}s  {'ESTÁVEL' if r<0 else 'INSTÁVEL'}")
        else:
            tau = 1/abs(r) if abs(r)>1e-10 else np.inf
            th = np.log(2)/abs(r) if abs(r)>1e-10 else np.inf
            modes.append({'Tipo':'Aper.','re':r,'im':0,'wn':0,'wd':0,'zeta':1 if r!=0 else 0,
                          'T':np.inf,'th':th,'stable':'SIM' if r<0 else ('NEUTRO' if abs(r)<1e-10 else 'NÃO')})
            print(f"\n  λ = {r:+.6f}  |  τ={tau:.2f}s  {'ESTÁVEL' if r<0 else 'INSTÁVEL' if r>1e-10 else 'NEUTRO'}")
        processed.add(i)
    return eigvals, eigvecs, modes

eigvals_long, _, modes_long = analyze_eigen(A_long, "LONGITUDINAL")
eigvals_lat, _, modes_lat = analyze_eigen(A_lat, "LATERO-DIRECIONAL")

# Identificação
osc_long = sorted([m for m in modes_long if m['Tipo']=='Oscil.'], key=lambda x: x['wn'])
if len(osc_long)>=2:
    osc_long[0]['nome']='FUGÓIDE'; osc_long[1]['nome']='PERÍODO CURTO'
    print(f"\n>> FUGÓIDE:       ωn={osc_long[0]['wn']:.4f}, ζ={osc_long[0]['zeta']:.4f}, T={osc_long[0]['T']:.1f}s")
    print(f">> PERÍODO CURTO: ωn={osc_long[1]['wn']:.4f}, ζ={osc_long[1]['zeta']:.4f}, T={osc_long[1]['T']:.1f}s")

osc_lat = [m for m in modes_lat if m['Tipo']=='Oscil.']
aper_lat = sorted([m for m in modes_lat if m['Tipo']=='Aper.'], key=lambda x: abs(x['re']), reverse=True)
if osc_lat: osc_lat[0]['nome']='DUTCH ROLL'; print(f">> DUTCH ROLL:    ωn={osc_lat[0]['wn']:.4f}, ζ={osc_lat[0]['zeta']:.4f}, T={osc_lat[0]['T']:.1f}s")
if len(aper_lat)>=2:
    aper_lat[0]['nome']='ROLL SUBSIDENCE'; aper_lat[1]['nome']='ESPIRAL'
    print(f">> ROLL:          λ={aper_lat[0]['re']:+.4f}, τ={1/abs(aper_lat[0]['re']):.3f}s")
    print(f">> ESPIRAL:       λ={aper_lat[1]['re']:+.6f}, T½/T₂={aper_lat[1]['th']:.1f}s ({aper_lat[1]['stable']})")

# ======================== FLYING QUALITIES ==================================
print(f"\n{'='*70}\n  QUALIDADES DE VOO (MIL-F-8785C, Classe IV Cat A)\n{'='*70}")
if len(osc_long)>=2:
    sp=osc_long[1]; ph=osc_long[0]
    n_alpha = CL_alpha * q_bar * S_ref / W0
    CAP = sp['wn']**2 / n_alpha
    print(f"  Short Period: ζ={sp['zeta']:.3f} {'[Nível 1: 0.35-1.30]' if 0.35<=sp['zeta']<=1.30 else '[VERIFICAR]'}")
    print(f"  CAP = {CAP:.3f} {'[Nível 1: 0.28-3.6]' if 0.28<=CAP<=3.6 else '[VERIFICAR]'}")
    print(f"  Fugóide: ζ={ph['zeta']:.4f} {'[Nível 1: >0.04]' if ph['zeta']>0.04 else '[Nível 2: >0]' if ph['zeta']>0 else '[INSTÁVEL]'}")
if osc_lat:
    dr=osc_lat[0]
    print(f"  Dutch Roll: ζ={dr['zeta']:.4f}, ωn={dr['wn']:.4f}, ζωn={dr['zeta']*dr['wn']:.4f}")
if len(aper_lat)>=2:
    tau_r = 1/abs(aper_lat[0]['re']) if abs(aper_lat[0]['re'])>0 else np.inf
    print(f"  Roll: τ={tau_r:.3f}s {'[Nível 1: <1.0s]' if tau_r<1.0 else '[VERIFICAR]'}")
    if aper_lat[1]['re']>0:
        print(f"  Espiral (instável): T₂={aper_lat[1]['th']:.1f}s {'[Nível 1: >12s]' if aper_lat[1]['th']>12 else '[VERIFICAR]'}")
    else:
        print(f"  Espiral: ESTÁVEL")

# ======================== PLOTS ============================================
out_dir = Path("outputs_dynamic"); out_dir.mkdir(exist_ok=True)

def time_response(A, x0, t):
    X = np.zeros((len(t), len(x0)))
    for i, ti in enumerate(t):
        X[i,:] = linalg.expm(A*ti) @ x0
    return X

# --- Plano complexo ---
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for ax, evs, title, colors in [
    (axes[0], eigvals_long, 'Longitudinal', ('#2196F3','#F44336')),
    (axes[1], eigvals_lat, 'Latero-Direcional', ('#4CAF50','#FF9800'))]:
    ax.axhline(0,color='k',lw=0.5); ax.axvline(0,color='k',lw=0.5)
    for ev in evs:
        c = colors[0] if abs(ev.imag)>1e-6 else colors[1]
        mk = 'o' if ev.real<0 else 'x'
        ax.plot(ev.real, ev.imag, mk, color=c, ms=10, mew=2)
    ax.set_xlabel('Re (1/s)'); ax.set_ylabel('Im (rad/s)'); ax.set_title(title)
plt.suptitle('Mapa de Autovalores — Estabilidade Dinâmica', fontsize=13, fontweight='bold')
plt.tight_layout(); plt.savefig(out_dir/'eigenvalue_map.png'); plt.close()

# --- Resposta longitudinal ---
t_sim = np.linspace(0, 120, 5000)
x0_long = np.array([0, 0.05, 0, 0])
X_long = time_response(A_long, x0_long, t_sim)
fig, axes = plt.subplots(2, 2, figsize=(14, 8))
for i,(ax,lbl,c) in enumerate(zip(axes.flat,
    [r'$\Delta u$ (m/s)',r'$\Delta\alpha$ (rad)',r'$\Delta q$ (rad/s)',r'$\Delta\theta$ (rad)'],
    ['#2196F3','#F44336','#4CAF50','#FF9800'])):
    ax.plot(t_sim, X_long[:,i], color=c, lw=1.5); ax.set_ylabel(lbl); ax.set_xlabel('t (s)')
plt.suptitle('Resposta Longitudinal — Perturbação Δα₀ = 0.05 rad', fontsize=13, fontweight='bold')
plt.tight_layout(); plt.savefig(out_dir/'long_time_response.png'); plt.close()

# --- Resposta lateral ---
x0_lat = np.array([0.05, 0, 0, 0])
X_lat = time_response(A_lat, x0_lat, t_sim)
fig, axes = plt.subplots(2, 2, figsize=(14, 8))
for i,(ax,lbl,c) in enumerate(zip(axes.flat,
    [r'$\Delta\beta$ (rad)',r'$\Delta p$ (rad/s)',r'$\Delta r$ (rad/s)',r'$\Delta\phi$ (rad)'],
    ['#9C27B0','#00BCD4','#E91E63','#8BC34A'])):
    ax.plot(t_sim, X_lat[:,i], color=c, lw=1.5); ax.set_ylabel(lbl); ax.set_xlabel('t (s)')
plt.suptitle('Resposta Latero-Direcional — Perturbação Δβ₀ = 0.05 rad', fontsize=13, fontweight='bold')
plt.tight_layout(); plt.savefig(out_dir/'lat_time_response.png'); plt.close()

# --- Zoom Short Period ---
t_sp = np.linspace(0, 5, 1000); X_sp = time_response(A_long, x0_long, t_sp)
fig,axes = plt.subplots(1,2,figsize=(12,5))
axes[0].plot(t_sp, np.degrees(X_sp[:,1]), '#F44336', lw=2); axes[0].set_ylabel(r'$\Delta\alpha$ (°)'); axes[0].set_xlabel('t (s)'); axes[0].set_title('α — Short Period')
axes[1].plot(t_sp, np.degrees(X_sp[:,2]), '#4CAF50', lw=2); axes[1].set_ylabel(r'$\Delta q$ (°/s)'); axes[1].set_xlabel('t (s)'); axes[1].set_title('q — Short Period')
plt.suptitle('Modo de Período Curto', fontsize=13, fontweight='bold')
plt.tight_layout(); plt.savefig(out_dir/'short_period_zoom.png'); plt.close()

# --- Zoom Dutch Roll ---
t_dr = np.linspace(0, 30, 2000); X_dr = time_response(A_lat, x0_lat, t_dr)
fig,axes = plt.subplots(1,2,figsize=(12,5))
axes[0].plot(t_dr, np.degrees(X_dr[:,0]), '#9C27B0', lw=2); axes[0].set_ylabel(r'$\Delta\beta$ (°)'); axes[0].set_xlabel('t (s)'); axes[0].set_title('β — Dutch Roll')
axes[1].plot(t_dr, np.degrees(X_dr[:,2]), '#E91E63', lw=2); axes[1].set_ylabel(r'$\Delta r$ (°/s)'); axes[1].set_xlabel('t (s)'); axes[1].set_title('r — Dutch Roll')
plt.suptitle('Modo Dutch Roll', fontsize=13, fontweight='bold')
plt.tight_layout(); plt.savefig(out_dir/'dutch_roll_zoom.png'); plt.close()

# ======================== TABELA FINAL =====================================
rows = []
if len(osc_long)>=2:
    for m in osc_long:
        rows.append({'Eixo':'Long.','Modo':m.get('nome','?'),'λ':f"{m['re']:+.4f}±{m['im']:.4f}j",
                     'ωn':f"{m['wn']:.4f}",'ζ':f"{m['zeta']:.4f}",'T(s)':f"{m['T']:.2f}",
                     'T½/T₂(s)':f"{m['th']:.2f}",'Estável':m['stable']})
if osc_lat:
    for m in osc_lat:
        rows.append({'Eixo':'Lat.','Modo':m.get('nome','?'),'λ':f"{m['re']:+.4f}±{m['im']:.4f}j",
                     'ωn':f"{m['wn']:.4f}",'ζ':f"{m['zeta']:.4f}",'T(s)':f"{m['T']:.2f}",
                     'T½/T₂(s)':f"{m['th']:.2f}",'Estável':m['stable']})
for m in aper_lat:
    rows.append({'Eixo':'Lat.','Modo':m.get('nome','?'),'λ':f"{m['re']:+.6f}",
                 'ωn':'—','ζ':'—','T(s)':'—','T½/T₂(s)':f"{m['th']:.2f}",'Estável':m['stable']})

df = pd.DataFrame(rows)
df.to_csv(out_dir/'dynamic_modes_summary.csv', index=False)
print(f"\n{'='*70}\n  TABELA RESUMO\n{'='*70}")
print(df.to_string(index=False))
print(f"\nTodos os arquivos salvos em: {out_dir}")