#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 ITENS 5.5 e 5.6 — Distribuição de Massas + Passeio de CG
=============================================================================
 5.5: Plot das massas distribuídas na aeronave com CG destacado
 5.6: Gráfico de passeio de CG para diferentes configurações de carga

 >>> TODAS AS POSIÇÕES E MASSAS SÃO VARIÁVEIS NO TOPO DO SCRIPT <<<
 >>> AJUSTE CONFORME DADOS DO CAD/SOLIDWORKS                     <<<
=============================================================================
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

plt.rcParams.update({
    'font.size': 11, 'axes.grid': True, 'grid.alpha': 0.3,
    'figure.dpi': 150, 'savefig.dpi': 200,
})

# ==========================================================================
# VARIÁVEIS DE ENTRADA — POSIÇÕES (X em metros, medido do nariz)
#                        MASSAS (em kg)
# ==========================================================================
# Referência: X = 0 no nariz da aeronave
# Comprimento total: 15.00 m
# Xref do AVL = 9.88 m (centro de gravidade nominal)

# --------------------------------------------------------------------------
#  COMPONENTE              |  X_cg (m)  |  Massa (kg)  |  Y_cg (m)
# --------------------------------------------------------------------------
# Cada componente: (nome, x_position, mass, y_position, cor)

COMPONENTS = {
    # === ESTRUTURA ===
    # Referência: Wempty = 13.663 kg (relatório Tabela 6)
    "Fuselagem (estrutura)": {
        "x": 8.00,         # centro geométrico da fuselagem (15m/2 + offset traseiro)
        "y": 0.00,
        "mass": 3600,       # ~26% do peso vazio — reforço naval, hook, catapulta
        "color": "#8ecae6",
        "marker": "s",
    },
    "Asa (estrutura)": {
        "x": 10.30,        # MAC da asa (~Xref)
        "y": 0.00,
        "mass": 2800,       # asa delta compósito + wing-fold
        "color": "#219ebc",
        "marker": "^",
    },
    "Canard (estrutura)": {
        "x": 5.20,         # centro do canard (entre 4.31 e 6.14 m)
        "y": 0.20,
        "mass": 420,
        "color": "#023047",
        "marker": "v",
    },
    "Empenagem vertical": {
        "x": 11.40,        # centro da VT (entre 10.39 e 12.49 m)
        "y": 2.10,
        "mass": 350,
        "color": "#126782",
        "marker": "D",
    },

    # === PROPULSÃO ===
    "Motor F135": {
        "x": 12.50,        # motor no terço traseiro
        "y": 0.00,
        "mass": 1701,       # peso seco F135-PW-100
        "color": "#e63946",
        "marker": "o",
    },
    "Bocal + afterburner": {
        "x": 14.00,        # parte mais traseira
        "y": 0.00,
        "mass": 350,
        "color": "#d62828",
        "marker": "h",
    },
    "Entrada de ar + dutos": {
        "x": 7.00,         # inlet ventral, região do canard/asa
        "y": -0.40,
        "mass": 450,
        "color": "#c1121f",
        "marker": "h",
    },

    # === SISTEMAS ===
    "Aviônicos + Radar AESA": {
        "x": 1.80,         # nariz (radome)
        "y": 0.00,
        "mass": 650,
        "color": "#f4a261",
        "marker": "p",
    },
    "Cockpit + Piloto + Assento": {
        "x": 3.50,         # cockpit
        "y": 0.50,
        "mass": 300,        # piloto ~100 + assento ejetável ~200
        "color": "#e9c46a",
        "marker": "*",
    },
    "Sistema hidráulico": {
        "x": 9.50,         # centro, perto do CG
        "y": -0.30,
        "mass": 300,
        "color": "#2a9d8f",
        "marker": "H",
    },
    "Sistema elétrico": {
        "x": 5.50,
        "y": -0.20,
        "mass": 250,
        "color": "#264653",
        "marker": "X",
    },
    "Sist. controle (FBW)": {
        "x": 7.50,
        "y": 0.10,
        "mass": 180,
        "color": "#6a994e",
        "marker": "d",
    },

    # === TREM DE POUSO ===
    "Trem dianteiro": {
        "x": 3.00,
        "y": -0.80,
        "mass": 280,
        "color": "#bc6c25",
        "marker": "v",
    },
    "Trem principal": {
        "x": 10.20,        # sob a asa, ligeiramente à frente do CG
        "y": -0.80,
        "mass": 820,        # reforçado para pouso embarcado
        "color": "#9b2226",
        "marker": "v",
    },

    # === OUTROS ===
    "Hook + reforço estrutural": {
        "x": 13.80,        # gancho de arresting na cauda
        "y": -0.50,
        "mass": 350,        # reforçado para pouso embarcado
        "color": "#774936",
        "marker": "P",
    },
    "Wing-fold + atuadores": {
        "x": 10.80,
        "y": 0.00,
        "mass": 280,
        "color": "#a68a64",
        "marker": "8",
    },
    "ECS + miscelânea": {
        "x": 8.50,
        "y": 0.00,
        "mass": 583,        # Environmental Control System + ajuste
        "color": "#adb5bd",
        "marker": "o",
    },
}

# === COMBUSTÍVEL (tanques distribuídos) ===
# Tanques: fuselagem central, asa esquerda, asa direita
FUEL_TANKS = {
    "Tanque fuselagem (fwd)": {
        "x": 8.00,          # tanque forward, entre cockpit e asa
        "y": -0.10,
        "mass_full": 4500,
        "color": "#ffbe0b",
        "order": 3,
    },
    "Tanque fuselagem (aft)": {
        "x": 11.00,         # tanque aft, atrás da asa
        "y": -0.10,
        "mass_full": 5500,
        "color": "#fb5607",
        "order": 2,
    },
    "Tanques de asa (par)": {
        "x": 10.30,         # nas asas, perto do MAC
        "y": 0.00,
        "mass_full": 4536,
        "color": "#ff006e",
        "order": 1,
    },
}

# === ARMAMENTO / PAYLOAD ===
# Missão Air-to-Air
PAYLOAD_AA = {
    "6× AIM-120C": {"x": 9.80, "y": -0.60, "mass": 1080, "color": "#7209b7"},
    "2× AIM-9X":   {"x": 11.00, "y": -0.40, "mass": 172,  "color": "#560bad"},
    "Aviônicos missão": {"x": 2.50, "y": 0.10, "mass": 1021, "color": "#480ca8"},
}

# Missão Strike
PAYLOAD_STRIKE = {
    "4× MK-83 JDAM":  {"x": 9.80, "y": -0.70, "mass": 1816, "color": "#7209b7"},
    "2× AIM-9X":      {"x": 11.00, "y": -0.40, "mass": 172,  "color": "#560bad"},
    "Aviônicos missão": {"x": 2.50, "y": 0.10, "mass": 1130, "color": "#480ca8"},
}

# ==========================================================================
# CÁLCULOS
# ==========================================================================

def calc_cg(components_dict_list):
    """Calcula CG a partir de lista de dicionários {x, mass}."""
    total_mass = 0
    moment_x = 0
    moment_y = 0
    for comp in components_dict_list:
        m = comp["mass"]
        total_mass += m
        moment_x += m * comp["x"]
        moment_y += m * comp.get("y", 0)
    x_cg = moment_x / total_mass if total_mass > 0 else 0
    y_cg = moment_y / total_mass if total_mass > 0 else 0
    return x_cg, y_cg, total_mass


def get_all_items_for_config(fuel_fraction=1.0, payload_dict=None):
    """Retorna lista de todos os componentes para uma dada configuração."""
    items = []
    
    # Estrutura + sistemas (sempre presentes)
    for name, data in COMPONENTS.items():
        items.append({"name": name, "x": data["x"], "y": data["y"],
                       "mass": data["mass"]})
    
    # Combustível
    for name, tank in FUEL_TANKS.items():
        items.append({"name": name, "x": tank["x"], "y": tank["y"],
                       "mass": tank["mass_full"] * fuel_fraction})
    
    # Payload
    if payload_dict:
        for name, data in payload_dict.items():
            items.append({"name": name, "x": data["x"],
                           "y": data.get("y", 0), "mass": data["mass"]})
    
    return items


# Verificação de massas
empty_mass = sum(c["mass"] for c in COMPONENTS.values())
fuel_total = sum(t["mass_full"] for t in FUEL_TANKS.values())
payload_aa = sum(p["mass"] for p in PAYLOAD_AA.values())
payload_strike = sum(p["mass"] for p in PAYLOAD_STRIKE.values())

print("=" * 65)
print("  DISTRIBUIÇÃO DE MASSAS — VERIFICAÇÃO")
print("=" * 65)
print(f"  Peso vazio (estrutura+sistemas):  {empty_mass:>8.0f} kg")
print(f"  Combustível máximo:               {fuel_total:>8.0f} kg")
print(f"  Payload Air-to-Air:               {payload_aa:>8.0f} kg")
print(f"  Payload Strike:                   {payload_strike:>8.0f} kg")
print(f"  ---")
print(f"  MTOW (AA):     {empty_mass + fuel_total + payload_aa:>8.0f} kg  "
      f"(ref: 30442 kg)")
print(f"  MTOW (Strike): {empty_mass + fuel_total + payload_strike:>8.0f} kg  "
      f"(ref: 30442 kg)")

# CG para MTOW
items_mtow = get_all_items_for_config(1.0, PAYLOAD_AA)
xcg_mtow, ycg_mtow, m_mtow = calc_cg(items_mtow)
print(f"\n  CG (MTOW, A-A):    X = {xcg_mtow:.3f} m  (ref AVL: 9.880 m)")

items_empty = get_all_items_for_config(0.0, None)
xcg_empty, _, m_empty = calc_cg(items_empty)
print(f"  CG (vazio):        X = {xcg_empty:.3f} m")

items_mid = get_all_items_for_config(0.5, PAYLOAD_AA)
xcg_mid, _, m_mid = calc_cg(items_mid)
print(f"  CG (meia-missão):  X = {xcg_mid:.3f} m")
print("=" * 65)

# ==========================================================================
# 5.5 — PLOT DE MASSAS DISTRIBUÍDAS
# ==========================================================================

fig, ax = plt.subplots(figsize=(16, 7))

# Silhueta simplificada da aeronave (vista lateral)
fuselage_x = [0, 1.5, 3.0, 4.0, 5.0, 7.0, 9.0, 11.0, 13.0, 14.5, 15.0,
              14.5, 13.5, 12.0, 11.0, 9.0, 7.0, 5.0, 4.0, 3.0, 1.5, 0]
fuselage_y = [0, 0.3, 0.6, 0.8, 0.9, 1.0, 1.0, 0.95, 0.8, 0.5, 0.2,
              -0.2, -0.5, -0.7, -0.8, -0.8, -0.7, -0.6, -0.5, -0.4, -0.2, 0]

# Canard (simplificado)
canard_x = [4.3, 6.14, 5.5, 4.3]
canard_y = [0.2, 0.2, 0.5, 0.2]

# Asa (delta, vista lateral = borda de ataque)
wing_x = [8.7, 11.9, 10.5, 8.7]
wing_y = [0.0, 0.0, -0.15, 0.0]

# Vertical tail
vtail_x = [10.4, 12.5, 11.8, 10.4]
vtail_y = [0.8, 0.8, 3.4, 0.8]

ax.fill(fuselage_x, fuselage_y, color='#dee2e6', alpha=0.4, edgecolor='#6c757d', lw=1.5)
ax.fill(canard_x, canard_y, color='#adb5bd', alpha=0.3, edgecolor='#6c757d', lw=1)
ax.fill(wing_x, wing_y, color='#adb5bd', alpha=0.3, edgecolor='#6c757d', lw=1)
ax.fill(vtail_x, vtail_y, color='#adb5bd', alpha=0.3, edgecolor='#6c757d', lw=1)

# Plotar cada componente
legend_handles = []
for name, data in COMPONENTS.items():
    size = max(40, data["mass"] / 8)  # tamanho proporcional à massa
    ax.scatter(data["x"], data["y"], s=size, c=data["color"],
               marker=data["marker"], edgecolors='black', linewidths=0.5,
               zorder=5, alpha=0.85)
    legend_handles.append(
        plt.Line2D([0], [0], marker=data["marker"], color='w',
                   markerfacecolor=data["color"], markersize=8,
                   markeredgecolor='black', markeredgewidth=0.5,
                   label=f'{name} ({data["mass"]} kg)')
    )

# Combustível
for name, tank in FUEL_TANKS.items():
    size = max(60, tank["mass_full"] / 6)
    ax.scatter(tank["x"], tank["y"], s=size, c=tank["color"],
               marker='s', edgecolors='black', linewidths=0.5,
               zorder=5, alpha=0.85)
    legend_handles.append(
        plt.Line2D([0], [0], marker='s', color='w',
                   markerfacecolor=tank["color"], markersize=8,
                   markeredgecolor='black', markeredgewidth=0.5,
                   label=f'{name} ({tank["mass_full"]} kg)')
    )

# Payload (A-A)
for name, data in PAYLOAD_AA.items():
    size = max(50, data["mass"] / 5)
    ax.scatter(data["x"], data.get("y", 0), s=size, c=data["color"],
               marker='P', edgecolors='black', linewidths=0.5,
               zorder=5, alpha=0.85)
    legend_handles.append(
        plt.Line2D([0], [0], marker='P', color='w',
                   markerfacecolor=data["color"], markersize=8,
                   markeredgecolor='black', markeredgewidth=0.5,
                   label=f'{name} ({data["mass"]} kg)')
    )

# CG marker
ax.plot(xcg_mtow, ycg_mtow, 'r^', markersize=18, zorder=10,
        markeredgecolor='black', markeredgewidth=1.5)
ax.annotate(f'CG (MTOW)\nX = {xcg_mtow:.2f} m',
            (xcg_mtow, ycg_mtow), textcoords="offset points",
            xytext=(15, 20), fontsize=11, fontweight='bold', color='red',
            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))

# Xref do AVL
ax.axvline(9.88, color='blue', ls='--', lw=1, alpha=0.5)
ax.annotate('X$_{ref}$ AVL = 9.88 m', (9.88, 3.2), fontsize=9,
            color='blue', ha='center')

legend_handles.append(
    plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='red',
               markersize=12, markeredgecolor='black', markeredgewidth=1,
               label=f'CG MTOW ({xcg_mtow:.2f} m)')
)

ax.set_xlabel('X [m] (do nariz)', fontsize=13)
ax.set_ylabel('Y [m]', fontsize=13)
ax.set_title('Distribuição de Massas e Centro de Gravidade — Configuração MTOW (Air-to-Air)',
             fontsize=14, fontweight='bold')
ax.set_xlim(-0.5, 16)
ax.set_ylim(-2.0, 4.0)
ax.set_aspect('equal')

ax.legend(handles=legend_handles, fontsize=7.5, loc='upper left',
          ncol=2, framealpha=0.9, bbox_to_anchor=(0.0, 1.0))

plt.tight_layout()
plt.savefig('outputs_dynamic/mass_distribution.png', dpi=200, bbox_inches='tight')
plt.close()
print("\n[OK] 5.5 — Mass distribution salvo: outputs_dynamic/mass_distribution.png")


# ==========================================================================
# 5.6 — PASSEIO DE CG
# ==========================================================================

fig2, axes2 = plt.subplots(1, 2, figsize=(16, 7))

# --- (a) CG vs fração de combustível (para diferentes payloads) ---
ax_a = axes2[0]

fuel_fracs = np.linspace(0, 1.0, 50)
configs = [
    ("MTOW Air-to-Air", PAYLOAD_AA, '#e63946', '-'),
    ("MTOW Strike", PAYLOAD_STRIKE, '#264653', '--'),
    ("Ferry (sem payload)", None, '#2a9d8f', '-.'),
]

c_ref = 2.76  # MAC

for label, payload, color, ls in configs:
    xcg_arr = []
    mass_arr = []
    for ff in fuel_fracs:
        items = get_all_items_for_config(ff, payload)
        xc, _, mt = calc_cg(items)
        xcg_arr.append(xc)
        mass_arr.append(mt)
    xcg_arr = np.array(xcg_arr)
    mass_arr = np.array(mass_arr)
    
    # Converter para %MAC
    xcg_mac = (xcg_arr - xcg_arr[0]) / c_ref * 100  # variação relativa
    
    ax_a.plot(fuel_fracs * 100, xcg_arr, color=color, ls=ls, lw=2, label=label)
    
    # Marcar pontos extremos
    ax_a.plot(0, xcg_arr[0], 'o', color=color, markersize=8)
    ax_a.plot(100, xcg_arr[-1], 's', color=color, markersize=8)

# Faixa aceitável de CG (±5% MAC do Xref)
xref = 9.88
margin = 0.05 * c_ref  # 5% MAC
ax_a.axhspan(xref - margin, xref + margin, alpha=0.15, color='green',
             label=f'Faixa aceitável (±5% MAC)')
ax_a.axhline(xref, color='green', ls=':', lw=1)

# Ponto neutro
Xnp = 9.886  # do AVL
ax_a.axhline(Xnp, color='red', ls='--', lw=1.5, label=f'Ponto Neutro (X$_{{np}}$ = {Xnp:.3f} m)')

ax_a.set_xlabel('Combustível [% do máximo]', fontsize=13)
ax_a.set_ylabel('X$_{CG}$ [m]', fontsize=13)
ax_a.set_title('Passeio de CG vs. Combustível', fontsize=13, fontweight='bold')
ax_a.legend(fontsize=9, loc='best')
ax_a.invert_xaxis()  # 100% (cheio) à esquerda, 0% (vazio) à direita

# --- (b) Diagrama de Loading (Massa vs X_CG) ---
ax_b = axes2[1]

# Sequência de carregamento típica:
# 1. Aeronave vazia
# 2. + Piloto + aviônicos
# 3. + Combustível parcial
# 4. + Payload
# 5. + Combustível total = MTOW

loading_sequence_AA = [
    ("Vazio operacional", 0.0, None),
    ("+ Combustível 25%", 0.25, None),
    ("+ Combustível 50%", 0.50, None),
    ("+ Combustível 75%", 0.75, None),
    ("+ Combustível 100%", 1.0, None),
    ("+ Payload A-A (MTOW)", 1.0, PAYLOAD_AA),
]

# Unloading sequence (missão):
# MTOW → consumo de combustível → lançamento de armas → pouso
unloading_AA = [
    ("MTOW (decolagem)", 1.0, PAYLOAD_AA),
    ("75% fuel", 0.75, PAYLOAD_AA),
    ("50% fuel (meia-missão)", 0.50, PAYLOAD_AA),
    ("50% fuel, sem mísseis", 0.50, {"Aviônicos missão": PAYLOAD_AA["Aviônicos missão"]}),
    ("25% fuel, sem mísseis", 0.25, {"Aviônicos missão": PAYLOAD_AA["Aviônicos missão"]}),
    ("Pouso (reserva)", 0.20, {"Aviônicos missão": PAYLOAD_AA["Aviônicos missão"]}),
]

# Loading
xcg_load = []; mass_load = []
for label, ff, pl in loading_sequence_AA:
    items = get_all_items_for_config(ff, pl)
    xc, _, mt = calc_cg(items)
    xcg_load.append(xc)
    mass_load.append(mt)

ax_b.plot(xcg_load, np.array(mass_load)/1000, 'b-o', lw=2, markersize=6,
          label='Carregamento', zorder=3)

# Unloading (missão)
xcg_unload = []; mass_unload = []
for label, ff, pl in unloading_AA:
    items = get_all_items_for_config(ff, pl)
    xc, _, mt = calc_cg(items)
    xcg_unload.append(xc)
    mass_unload.append(mt)

ax_b.plot(xcg_unload, np.array(mass_unload)/1000, 'r--s', lw=2, markersize=6,
          label='Missão (consumo + lançamento)', zorder=3)

# Anotar pontos
for i, (label, _, _) in enumerate(loading_sequence_AA):
    if i in [0, len(loading_sequence_AA)-1]:
        ax_b.annotate(label, (xcg_load[i], mass_load[i]/1000),
                       textcoords="offset points", xytext=(8, -12),
                       fontsize=8, color='blue')

for i, (label, _, _) in enumerate(unloading_AA):
    if i in [0, len(unloading_AA)-1]:
        ax_b.annotate(label, (xcg_unload[i], mass_unload[i]/1000),
                       textcoords="offset points", xytext=(8, 8),
                       fontsize=8, color='red')

# Limites
ax_b.axvspan(xref - margin, xref + margin, alpha=0.15, color='green',
             label=f'Faixa aceitável')
ax_b.axvline(Xnp, color='red', ls='--', lw=1.5, alpha=0.7,
             label=f'Ponto Neutro')

ax_b.set_xlabel('X$_{CG}$ [m]', fontsize=13)
ax_b.set_ylabel('Massa [ton]', fontsize=13)
ax_b.set_title('Diagrama de Carregamento (Potato Diagram)', fontsize=13, fontweight='bold')
ax_b.legend(fontsize=9, loc='best')

plt.suptitle('Análise de Centro de Gravidade — Passeio de CG',
             fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('outputs_dynamic/cg_travel.png', dpi=200, bbox_inches='tight')
plt.close()
print("[OK] 5.6 — CG travel salvo: outputs_dynamic/cg_travel.png")


# ==========================================================================
# TABELA RESUMO
# ==========================================================================
print(f"\n{'='*75}")
print(f"  RESUMO DE PASSEIO DE CG")
print(f"{'='*75}")
print(f"{'Configuração':<40} {'Massa [kg]':>10} {'X_CG [m]':>10} {'SM [%MAC]':>10}")
print(f"{'-'*75}")

configs_summary = [
    ("Vazio operacional (OEW)", 0.0, None),
    ("Ferry (fuel 100%, sem payload)", 1.0, None),
    ("MTOW Air-to-Air", 1.0, PAYLOAD_AA),
    ("MTOW Strike", 1.0, PAYLOAD_STRIKE),
    ("Meia-missão A-A (50% fuel)", 0.50, PAYLOAD_AA),
    ("Retorno (25% fuel, sem armas)", 0.25, {"Aviônicos missão": PAYLOAD_AA["Aviônicos missão"]}),
    ("Pouso (20% fuel, reserva)", 0.20, {"Aviônicos missão": PAYLOAD_AA["Aviônicos missão"]}),
]

Xnp = 9.886
for label, ff, pl in configs_summary:
    items = get_all_items_for_config(ff, pl)
    xc, _, mt = calc_cg(items)
    sm = (Xnp - xc) / c_ref * 100
    print(f"{label:<40} {mt:10.0f} {xc:10.3f} {sm:10.2f}")

print(f"\n  Ponto Neutro:     X_np = {Xnp:.3f} m")
print(f"  MAC:              c_ref = {c_ref:.3f} m")
print(f"  Excursão total de CG: {max(xcg_load+xcg_unload) - min(xcg_load+xcg_unload):.3f} m "
      f"({(max(xcg_load+xcg_unload) - min(xcg_load+xcg_unload))/c_ref*100:.1f}% MAC)")
print(f"{'='*75}")