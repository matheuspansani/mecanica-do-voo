#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AVL batch runner (Mac-friendly) - TRIM 100% robusto via ANGLE do canard (all-moving)

O que este script faz:
- Gera outputs/aircraft.avl a partir dos PARAMS
- Roda sweep de alpha (FS + ST por alpha) e salva outputs/results_alpha_sweep.csv
- Faz trimagem para CL alvo ajustando a incidência (ANGLE) do canard até Cm ~ 0
  (loop externo em Python com bisseção) — evita "Trim convergence failed" e NaN/Infinity.
- Plota Cm(alpha), CL(alpha), CD(alpha)
- Abre XQuartz para visualizar a geometria (opcional)

OBS:
- Para "canard 100% móvel", NÃO usamos CONTROL no canard. A variável é o ANGLE do canard.
- Você ainda pode manter CONTROL na asa/leme se quiser; aqui o trim não depende deles.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =========================
# 1) EDIT YOUR PARAMETERS
# =========================
PARAMS: Dict = {
    "project_name": "CACA_UFU_POS_REAL_NACA64A005",
    "avl_exe": "/Users/matheuspansani/Downloads/avl",
    "show_geometry_in_xquartz": True,

    "refs": {
        "Sref": 32.420,
        "Cref": 2.76,
        "Bref": 11.72,
        "Xref": 9.88,
        "Yref": 0.00,
        "Zref": 0.00,
    },

    "cases": {
        "alpha_deg": list(np.linspace(-4, 12, 9)),
        "beta_deg": 0.0,
        "controls": {},  # ex: {"ail": 0.0, "rud": 0.0}
    },

    "paneling": {
        "Nspan_w": 20, "Nchord_w": 8,
        "Nspan_c": 10, "Nchord_c": 5,
        "Nspan_v": 10, "Nchord_v": 5,
    },

    "airfoils": {
        "main": "airfoils/NACA64A005.dat"
    },

    # >>> CANARD ALL-MOVING VIA ANGLE (incidence_deg)
    "canard": {
        "name": "CANARD",
        "incidence_deg": 0.0,  # <- variável de trim
        "airfoil_file": "airfoils/NACA64A005.dat",
        "sections": [
            (4.310, 0.00, 0.20, 2.62, 0.0),
            (6.140, 2.37, 0.20, 0.79, 0.0),
        ],
        "control": {"enabled": False},  # não usar hinge/control no canard
    },

    "wing": {
        "name": "WING",
        "incidence_deg": 0.0,
        "airfoil_file": "airfoils/NACA64A005.dat",
        "sections": [
            (8.755,  0.00, 0.00, 4.32, 0.0),
            (10.275, 2.50, 0.00, 2.80, 0.0),
            (11.865, 5.80, 0.00, 1.21, 0.0),
        ],
        "control": {"enabled": True, "name": "ail", "gain": 1.0, "x_hinge": 0.75, "sign": -1.0},
    },

    "vtail": {
        "name": "SINGLE_TAIL",
        "incidence_deg": 0.0,
        "airfoil_file": "airfoils/NACA64A005.dat",
        "sections": [
            (10.394, 0.00, 0.80, 2.92, 0.0),
            (12.494, 0.00, 3.43, 0.88, 0.0),
        ],
        "control": {"enabled": True, "name": "rud", "gain": 1.0, "x_hinge": 0.65, "sign": 1.0},
    },
    "trim": {
    "enabled": True,
    "cl_list": [0.10, 0.20, 0.30, 0.40, 0.50],  # ajuste como quiser
    "beta_deg": 0.0,
    "cm_target": 0.0,
    "bracket_deg": (-3.0, 3.0),
    "tol_cm": 1e-4,
    "max_iter": 25,
}
}

# =========================
# 2) FILE GENERATION
# =========================

def _fmt(x: float) -> str:
    return f"{x:.6g}"
def run_trim_sweep_and_save(params: Dict, out_dir: Path) -> pd.DataFrame:
    """
    Roda trimagem (canard via ANGLE) para vários CLs e salva outputs/trim_summary.csv.
    Cada CL target usa tags únicos (com CL embutido) para evitar sobrescrita.
    """
    t = params.get("trim", {})
    cl_list = [float(x) for x in t.get("cl_list", [0.2])]
    beta = float(t.get("beta_deg", 0.0))
    bracket = tuple(t.get("bracket_deg", (-3.0, 3.0)))
    tol_cm = float(t.get("tol_cm", 1e-4))
    max_iter = int(t.get("max_iter", 25))

    rows = []

    for cl in cl_list:
        print(f"\n[AVL] Trim sweep: CL={cl:.3f} ...")
        try:
            trim = trim_canard_by_incidence(
                params,
                out_dir,
                target_cl=cl,
                beta=beta,
                bracket=(float(bracket[0]), float(bracket[1])),
                tol_cm=tol_cm,
                max_iter=max_iter,
            )

            # Busca o CL real do último FT escrito para validação
            cl_tag = f"cl{cl:.3f}".replace(".", "p")
            cl_achieved = np.nan
            # Procura o último ft_trim_<cl_tag>_it*.txt gerado
            ft_candidates = sorted(out_dir.glob(f"ft_trim_{cl_tag}_it*.txt"))
            if ft_candidates:
                ft_last = parse_ft_file(ft_candidates[-1])
                cl_achieved = ft_last.get("CL", np.nan)

            rows.append({
                "CL_target": cl,
                "CL_achieved": cl_achieved,
                "beta_deg": beta,
                "canard_incidence_deg": trim["canard_incidence_deg"],
                "alpha_trim_deg": trim["alpha_trim_deg"],
                "Cm_final": trim["cm"],
                "status": "OK",
            })
        except Exception as e:
            rows.append({
                "CL_target": cl,
                "CL_achieved": np.nan,
                "beta_deg": beta,
                "canard_incidence_deg": np.nan,
                "alpha_trim_deg": np.nan,
                "Cm_final": np.nan,
                "status": f"FAIL: {type(e).__name__}: {e}",
            })

    df_trim = pd.DataFrame(rows).sort_values("CL_target").reset_index(drop=True)
    out_csv = out_dir / "trim_summary.csv"
    df_trim.to_csv(out_csv, index=False)
    print(f"\n[OK] Resumo de trimagem salvo em: {out_csv}")

    # Imprime tabela no terminal
    print(df_trim.to_string(index=False))
    return df_trim

def generate_avl_text(params: Dict) -> str:
    refs = params["refs"]
    pan = params["paneling"]
    wing = params["wing"]
    can = params["canard"]
    vt = params["vtail"]

    lines: List[str] = []
    lines.append(params["project_name"])
    lines.append("0.0")
    lines.append("0 0 0")
    lines.append(f'{_fmt(refs["Sref"])}  {_fmt(refs["Cref"])}  {_fmt(refs["Bref"])}')
    lines.append(f'{_fmt(refs["Xref"])}  {_fmt(refs["Yref"])}  {_fmt(refs["Zref"])}')
    lines.append("0.020")
    lines.append("")

    def add_surface(surface: Dict, nchord_key: str, nspan_key: str, yduplicate: bool):
        lines.append("SURFACE")
        lines.append(surface["name"])
        lines.append(f'{pan[nchord_key]} 1.0  {pan[nspan_key]}  -1.0')
        if yduplicate:
            lines.append("YDUPLICATE")
            lines.append("0.0")
        lines.append("ANGLE")
        lines.append(_fmt(float(surface.get("incidence_deg", 0.0))))
        lines.append("")

        ctrl = surface.get("control", {"enabled": False})
        for idx, (x, y, z, c, tw) in enumerate(surface["sections"]):
            lines.append("SECTION")
            lines.append(f'{_fmt(x)}  {_fmt(y)}  {_fmt(z)}  {_fmt(c)}  {_fmt(tw)}')

            if surface.get("airfoil_file"):
                lines.append("AFILE")
                lines.append(surface["airfoil_file"])
            else:
                lines.append("NACA")
                lines.append("0012")

            # Controle apenas se estiver habilitado
            if ctrl.get("enabled", False) and idx == 0:
                # name gain xhinge yhinge zhinge sign
                xh = float(ctrl.get("x_hinge", 0.75))
                lines.append("CONTROL")
                lines.append(f'{ctrl["name"]}  {_fmt(float(ctrl["gain"]))}  {_fmt(xh)}  0.0  0.0  {_fmt(float(ctrl["sign"]))}')
        lines.append("")

    add_surface(wing, "Nchord_w", "Nspan_w", yduplicate=True)
    add_surface(can,  "Nchord_c", "Nspan_c", yduplicate=True)
    add_surface(vt,   "Nchord_v", "Nspan_v", yduplicate=False)

    return "\n".join(lines)

def generate_avl_command_script_sweep(params: Dict, out_dir: Path) -> str:
    """
    Gera script de comandos AVL 3.40 para sweep de alpha.

    Sintaxe AVL 3.40 dentro de .OPER:
      A A <val>  → seta variável Alpha, constraint alpha, valor <val>  (1 linha, sem submenu)
      B B <val>  → seta variável Beta,  constraint beta,  valor <val>  (1 linha, sem submenu)
      X          → executa o caso
      ST <file>  → salva stability derivatives no arquivo
      FT <file>  → salva total forces no arquivo

    Caminhos de arquivo relativos ao diretório do projeto (cwd do AVL).
    AVL Fortran tem limite de ~80 chars para nomes — usamos caminhos curtos.
    """
    cases = params["cases"]
    alpha_list = cases["alpha_deg"]
    beta = float(cases.get("beta_deg", 0.0))

    # Calcula caminho relativo de out_dir em relação ao cwd (raiz do projeto)
    try:
        out_rel = out_dir.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        out_rel = out_dir

    lines: List[str] = []
    lines.append("OPER")

    # Seta beta uma vez (sintaxe segura: variável B, constraint B, valor)
    if beta != 0.0:
        lines.append(f"B B {_fmt(beta)}")

    for a in alpha_list:
        # Seta alpha (sintaxe segura: variável A, constraint A, valor)
        lines.append(f"A A {_fmt(float(a))}")
        lines.append("X")
        # ST e FT com filename na MESMA linha
        # Caminho relativo ao projeto (cwd do AVL)
        lines.append(f"ST {out_rel / f'st_alpha_{float(a):+06.2f}.txt'}")
        lines.append(f"FT {out_rel / f'ft_alpha_{float(a):+06.2f}.txt'}")

    # Linha vazia sai do .OPER de volta ao menu principal AVL
    lines.append("")
    lines.append("QUIT")
    return "\n".join(lines) + "\n"

# =========================
# 3) RUN AVL & PARSE
# =========================

def run_avl_batch(avl_exe: str, avl_file: Path, cmd_script_text: str, out_dir: Path,
                  log_name: str = "avl_stdout_stderr.log") -> Tuple[int, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / log_name

    # Salva script de comandos em arquivo .cmd para debug
    cmd_file = out_dir / (log_name.replace(".log", ".cmd"))
    cmd_file.write_text(cmd_script_text, encoding="utf-8")

    if not shutil.which(avl_exe) and not Path(avl_exe).exists():
        raise FileNotFoundError(f"AVL executável não encontrado: {avl_exe}")

    # Roda AVL com cwd = diretório raiz do projeto
    # para que referências de airfoil (airfoils/xxx.dat) funcionem.
    # Os nomes de arquivo FT/ST nos scripts já usam caminhos relativos (ex: outputs/ft_*.txt).
    project_root = Path.cwd()

    proc = subprocess.run(
        [avl_exe, str(avl_file.resolve())],
        input=cmd_script_text,
        text=True,
        capture_output=True,
        cwd=str(project_root),
    )

    log_text = proc.stdout + "\n\n--- STDERR ---\n" + proc.stderr
    log_path.write_text(log_text, encoding="utf-8")

    # Validação: se returncode != 0 E stderr contém erro Fortran, levantar exceção
    if proc.returncode != 0 and ("Fortran runtime error" in proc.stderr or "STOP" in proc.stderr):
        tail_lines = log_text.splitlines()[-30:]
        raise RuntimeError(
            f"AVL saiu com returncode={proc.returncode} (log={log_path}).\n"
            f"Últimas linhas:\n" + "\n".join(tail_lines)
        )

    return proc.returncode, str(log_path)

_float_re = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?"

def parse_fs_file(fs_path: Path) -> Dict[str, float]:
    """Parser antigo (FS). Mantido por compatibilidade — não mais usado pelo sweep."""
    if not fs_path.exists():
        return {}
    text = fs_path.read_text(errors="ignore")

    def find_coeff(label: str) -> Optional[float]:
        # Case-sensitive
        patterns = [
            rf"(?<![a-zA-Z]){re.escape(label)}tot(?![a-zA-Z])\s*=\s*({_float_re})",
            rf"(?<![a-zA-Z]){re.escape(label)}(?![a-zA-Z])\s*=\s*({_float_re})",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return float(m.group(1))
        return None

    out: Dict[str, float] = {}
    for k in ["CL", "CD", "Cm", "CY", "Cl", "Cn"]:
        v = find_coeff(k)
        if v is not None and np.isfinite(v):
            out[k] = float(v)
    return out

def parse_st_file(st_path: Path) -> Dict[str, float]:
    if not st_path.exists():
        return {}
    text = st_path.read_text(errors="ignore")
    out: Dict[str, float] = {}

    m_xnp = re.search(rf"(?:Xnp|X_NP)\s*[:=]\s*({_float_re})", text)
    if not m_xnp:
        m_xnp = re.search(rf"Neutral\s*point.*X\s*[:=]\s*({_float_re})", text, re.IGNORECASE)
    if m_xnp:
        out["Xnp"] = float(m_xnp.group(1))

    m_alpha = re.search(rf"\bAlpha\s*=\s*({_float_re})", text)
    if m_alpha:
        out["alpha"] = float(m_alpha.group(1))

    # Derivativas de estabilidade — case-sensitive para evitar Cma ≠ CMA etc.
    keys = ["CLa", "CLb", "CYa", "CYb", "Cla", "Clb", "Cma", "Cmb", "Cna", "Cnb",
            "CLq", "Cmq", "CLp", "Clp", "CYp", "Cnp", "CLr", "Clr", "CYr", "Cnr"]
    for key in keys:
        m2 = re.search(rf"(?<![a-zA-Z]){re.escape(key)}(?![a-zA-Z])\s*[:=]\s*({_float_re})", text)
        if m2:
            out[key] = float(m2.group(1))

    return out

def collect_results(out_dir: Path, alpha_list: List[float]) -> pd.DataFrame:
    rows = []
    for a in alpha_list:
        ft = out_dir / f"ft_alpha_{float(a):+06.2f}.txt"
        st = out_dir / f"st_alpha_{float(a):+06.2f}.txt"
        row = {"alpha_deg": float(a)}
        if ft.exists():
            row.update(parse_ft_file(ft))
        if st.exists():
            row.update(parse_st_file(st))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("alpha_deg").reset_index(drop=True)

def plot_basic(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    def _plot(ycol: str, title: str, fname: str):
        if ycol not in df.columns:
            return
        plt.figure()
        plt.plot(df["alpha_deg"], df[ycol], marker="o")
        plt.xlabel("alpha (deg)")
        plt.ylabel(ycol)
        plt.title(title)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(out_dir / fname, dpi=160)
        plt.close()

    _plot("Cm", "Pitching moment coefficient vs alpha", "Cm_vs_alpha.png")
    _plot("CL", "Lift coefficient vs alpha", "CL_vs_alpha.png")
    _plot("CD", "Drag coefficient vs alpha", "CD_vs_alpha.png")

def delete_if_exists(p: Path) -> None:
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass

# =========================
# 4) TRIM VIA CANARD ANGLE
# =========================

def generate_oper_cl_only_script(out_dir: Path, target_cl: float, beta: float = 0.0, tag: str = "trim") -> str:
    """
    Roda 1 caso em .OPER com constraint Alpha -> CL = target_cl.
    Salva FT (total forces) + ST (stability derivatives) em arquivo.

    Caminhos de arquivo relativos ao diretório do projeto (cwd do AVL).
    AVL Fortran tem limite de ~80 chars para nomes.
    """
    # Caminho relativo de out_dir em relação ao cwd (raiz do projeto)
    try:
        out_rel = out_dir.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        out_rel = out_dir

    ft_rel = out_rel / f"ft_{tag}.txt"
    st_rel = out_rel / f"st_{tag}.txt"

    lines: List[str] = []
    lines.append("OPER")
    if beta != 0.0:
        lines.append(f"B B {_fmt(beta)}")
    lines.append(f"A C {_fmt(target_cl)}")
    lines.append("X")
    lines.append(f"FT {ft_rel}")
    lines.append(f"ST {st_rel}")
    lines.append("")
    lines.append("QUIT")
    return "\n".join(lines) + "\n"

def parse_alpha_from_st(st_path: Path) -> Optional[float]:
    if not st_path.exists():
        return None
    text = st_path.read_text(errors="ignore")
    m = re.search(rf"\bAlpha\s*=\s*({_float_re})", text, re.IGNORECASE)
    return float(m.group(1)) if m else None

def run_case_get_cm_alpha(avl_exe: str, avl_file: Path, out_dir: Path, target_cl: float, beta: float, tag: str) -> Tuple[Optional[float], Optional[float]]:
    ft_path = out_dir / f"ft_{tag}.txt"
    st_path = out_dir / f"st_{tag}.txt"

    # Remove arquivos anteriores para evitar prompt "File exists. Append/Overwrite/Cancel"
    delete_if_exists(ft_path)
    delete_if_exists(st_path)

    cmd = generate_oper_cl_only_script(out_dir, target_cl, beta=beta, tag=tag)
    run_avl_batch(avl_exe, avl_file, cmd, out_dir, log_name=f"avl_{tag}.log")

    ft = parse_ft_file(ft_path)
    cm = ft.get("Cm", None)

    alpha = parse_alpha_from_st(st_path)  # pode ser None em alguns builds
    return cm, alpha

def trim_canard_by_incidence(params: Dict, out_dir: Path, target_cl: float, beta: float = 0.0,
                             bracket: Tuple[float, float] = (-3.0, 3.0),
                             tol_cm: float = 1e-4, max_iter: int = 30) -> Dict[str, float]:
    lo, hi = float(bracket[0]), float(bracket[1])

    # Tag base inclui CL alvo para evitar colisão de arquivos entre CL targets
    cl_tag = f"cl{target_cl:.3f}".replace(".", "p")

    def eval_at(inc: float, tag: str) -> Tuple[float, Optional[float]]:
        params["canard"]["incidence_deg"] = float(inc)

        # regenera .avl
        avl_text = generate_avl_text(params)
        avl_file = out_dir / "aircraft.avl"
        avl_file.write_text(avl_text, encoding="utf-8")

        # Remove arquivos antigos do mesmo tag para evitar leitura de dados stale
        for suffix in ("ft_", "st_"):
            old = out_dir / f"{suffix}{tag}.txt"
            delete_if_exists(old)

        cm, alpha = run_case_get_cm_alpha(params["avl_exe"], avl_file, out_dir, target_cl, beta, tag=tag)

        if cm is None or (not np.isfinite(cm)):
            # Mostra o log do caso para facilitar
            logp = out_dir / f"avl_{tag}.log"
            tail = ""
            if logp.exists():
                tail = "\n".join(logp.read_text(errors="ignore").splitlines()[-25:])
            raise RuntimeError(
                f"AVL não retornou Cm válido (tag={tag}) para canard_inc={inc}.\n"
                f"Últimas linhas do log:\n{tail}"
            )
        return float(cm), alpha

    # avalia extremos
    cm_lo, a_lo = eval_at(lo, tag=f"trim_{cl_tag}_lo")
    cm_hi, a_hi = eval_at(hi, tag=f"trim_{cl_tag}_hi")

    # se não mudou de sinal, expande aos poucos (até 3 vezes)
    expand_steps = [5.0, 10.0, 15.0]
    for step in expand_steps:
        if cm_lo * cm_hi <= 0:
            break
        lo2, hi2 = lo - step, hi + step
        cm_lo2, a_lo2 = eval_at(lo2, tag=f"trim_{cl_tag}_lo_m{int(step)}")
        cm_hi2, a_hi2 = eval_at(hi2, tag=f"trim_{cl_tag}_hi_p{int(step)}")
        lo, hi, cm_lo, cm_hi, a_lo, a_hi = lo2, hi2, cm_lo2, cm_hi2, a_lo2, a_hi2

    if cm_lo * cm_hi > 0:
        raise RuntimeError(
            f"Não consegui bracketear Cm=0: Cm({lo:+.1f})={cm_lo:+.4g}, Cm({hi:+.1f})={cm_hi:+.4g}. "
            f"Talvez Cm não cruze zero nesse CL, ou o eixo/ref está estranho."
        )

    best_inc = None
    best_cm = None
    best_alpha = None

    for k in range(max_iter):
        mid = 0.5 * (lo + hi)
        cm_mid, a_mid = eval_at(mid, tag=f"trim_{cl_tag}_it{k:02d}")

        if best_cm is None or abs(cm_mid) < abs(best_cm):
            best_cm, best_inc, best_alpha = cm_mid, mid, a_mid

        if abs(cm_mid) < tol_cm:
            # Validação pós-trim: verifica se CL obtido bate com alvo
            ft_final = out_dir / f"ft_trim_{cl_tag}_it{k:02d}.txt"
            ft_data = parse_ft_file(ft_final)
            cl_achieved = ft_data.get("CL", None)
            if cl_achieved is not None:
                cl_err = abs(cl_achieved - target_cl)
                if cl_err > 0.05:
                    print(f"  [AVISO] CL obtido={cl_achieved:.5f} difere do alvo {target_cl:.3f} (delta={cl_err:.4f})")
                else:
                    print(f"  [OK] CL obtido={cl_achieved:.5f} (alvo={target_cl:.3f}, delta={cl_err:.5f})")

            return {"canard_incidence_deg": mid, "alpha_trim_deg": float(a_mid) if a_mid is not None else float("nan"), "cm": cm_mid}

        if cm_lo * cm_mid <= 0:
            hi, cm_hi, a_hi = mid, cm_mid, a_mid
        else:
            lo, cm_lo, a_lo = mid, cm_mid, a_mid

    assert best_inc is not None and best_cm is not None
    return {"canard_incidence_deg": float(best_inc), "alpha_trim_deg": float(best_alpha) if best_alpha is not None else float("nan"), "cm": float(best_cm)}

# =========================
# 5) XQUARTZ INTERACTIVE
# =========================

def show_in_xquartz(avl_exe: str, avl_file: Path):
    print("\n[GUI] Abrindo XQuartz para visualização da geometria...")
    os.environ["DISPLAY"] = ":0"
    try:
        p = subprocess.Popen(
            [avl_exe, str(avl_file)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )
        assert p.stdin is not None
        p.stdin.write("oper\ng\n")
        p.stdin.flush()
        print(">> O desenho deve ter aberto no XQuartz.")
        print(">> Você pode usar as setas do teclado no Xplot11 para girar o avião.")
        input(">>> Pressione ENTER aqui neste terminal para fechar o desenho e encerrar o script... <<<")
        p.stdin.write("\n\nquit\n")
        p.stdin.flush()
    except Exception as e:
        print(f"[ERRO GUI] Não foi possível abrir o XQuartz: {e}")
    finally:
        try:
            p.terminate()
        except Exception:
            pass

def parse_ft_file(ft_path: Path) -> Dict[str, float]:
    """
    Parser do 'FT' (total forces).

    IMPORTANTE — busca CASE-SENSITIVE:
      - CLtot (lift total)  ≠  Cltot (rolling-moment total)
      - CDtot (drag total)  ≠  ... (sem conflito mas mantemos consistência)
      - Cmtot (pitching)    ≠  ... (idem)

    O arquivo AVL FT típico contém:
        CXtot =  0.00123   Cltot = -0.00000   Cl'tot = -0.00000
        CYtot =  0.00000   Cmtot = -0.00624
        CZtot = -0.24947   Cntot =  0.00000   Cn'tot =  0.00000
        CLtot =  0.24947
        CDtot =  0.00762
        ...

    Se usarmos IGNORECASE, "CLtot" casa primeiro com "Cltot" (rolling moment ≈ 0).
    Portanto as buscas aqui são CASE-SENSITIVE.
    """
    if not ft_path.exists():
        return {}
    text = ft_path.read_text(errors="ignore")

    def find_case_sensitive(labels: List[str]) -> Optional[float]:
        """Busca case-sensitive, retorna o primeiro match."""
        for lab in labels:
            # \b não é suficiente para diferenciar CL de Cl; usamos lookahead/behind explícito
            m = re.search(rf"(?<![a-zA-Z]){re.escape(lab)}(?![a-zA-Z])\s*=\s*({_float_re})", text)
            if m:
                return float(m.group(1))
        return None

    out: Dict[str, float] = {}
    cl = find_case_sensitive(["CLtot", "CL"])
    cd = find_case_sensitive(["CDtot", "CDff", "CD"])
    cm = find_case_sensitive(["Cmtot", "Cm"])
    cy = find_case_sensitive(["CYtot", "CY"])
    cl_roll = find_case_sensitive(["Cltot", "Cl"])    # rolling moment (minúsculo 'l')
    cn = find_case_sensitive(["Cntot", "Cn"])

    if cl is not None and np.isfinite(cl): out["CL"] = cl
    if cd is not None and np.isfinite(cd): out["CD"] = cd
    if cm is not None and np.isfinite(cm): out["Cm"] = cm
    if cy is not None and np.isfinite(cy): out["CY"] = cy
    if cl_roll is not None and np.isfinite(cl_roll): out["Cl"] = cl_roll
    if cn is not None and np.isfinite(cn): out["Cn"] = cn
    return out

# =========================
# 6) MAIN
# =========================

def main():
    base = Path.cwd()
    out_dir = base / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    # garante canard sem CONTROL (all-moving via ANGLE)
    if "control" in PARAMS["canard"]:
        PARAMS["canard"]["control"]["enabled"] = False

    # Gera .avl inicial
    avl_text = generate_avl_text(PARAMS)
    avl_file = out_dir / "aircraft.avl"
    avl_file.write_text(avl_text, encoding="utf-8")

    # --- 1) SWEEP DE ALPHA ---
    print("[AVL] Rodando Sweep de Alpha (Estabilidade)...")
    for a in PARAMS["cases"]["alpha_deg"]:
        delete_if_exists(out_dir / f"st_alpha_{float(a):+06.2f}.txt")
        delete_if_exists(out_dir / f"ft_alpha_{float(a):+06.2f}.txt")

    cmd_sweep = generate_avl_command_script_sweep(PARAMS, out_dir)
    run_avl_batch(PARAMS["avl_exe"], avl_file, cmd_sweep, out_dir, "avl_sweep.log")

    alpha_list = [float(a) for a in PARAMS["cases"]["alpha_deg"]]
    df = collect_results(out_dir, alpha_list)

    csv_path = out_dir / "results_alpha_sweep.csv"
    df.to_csv(csv_path, index=False)
    print(f"[OK] Dados salvos em: {csv_path}")
    plot_basic(df, out_dir)

    # --- 2) TRIMAGEM VIA ANGLE DO CANARD ---
    target_cl = 0.2
    beta = float(PARAMS["cases"].get("beta_deg", 0.0))

    # limpa arquivos de iterações anteriores (incluindo tags com CL embutido)
    for p in out_dir.glob("ft_trim*.txt"):
        delete_if_exists(p)
    for p in out_dir.glob("st_trim*.txt"):
        delete_if_exists(p)
    for p in out_dir.glob("avl_trim*.log"):
        delete_if_exists(p)
    for p in out_dir.glob("avl_trim*.cmd"):
        delete_if_exists(p)

    print(f"\n[AVL] Trim (canard all-moving via ANGLE) para CL = {target_cl} e Cm ~ 0 ...")
    if PARAMS.get("trim", {}).get("enabled", True):
        df_trim = run_trim_sweep_and_save(PARAMS, out_dir)

    # usa o CL=0.2 (ou o mais próximo) para mostrar no RESUMO do terminal
    target_for_summary = 0.2
    i_best = (df_trim["CL_target"] - target_for_summary).abs().idxmin()
    trim_row = df_trim.loc[i_best].to_dict()

    # Para manter seu resumo atual:
    trim = {
        "canard_incidence_deg": float(trim_row.get("canard_incidence_deg", np.nan)),
        "alpha_trim_deg": float(trim_row.get("alpha_trim_deg", np.nan)),
        "cm": float(trim_row.get("Cm_final", np.nan)),
    }

    # --- 3) RESUMO ---
    print("\n" + "=" * 55)
    print("         RESUMO DA ANÁLISE AERODINÂMICA - UFU")
    print("=" * 55)

    # Estabilidade (do sweep)
    if "Xnp" in df.columns:
        xnp = df["Xnp"].iloc[len(df) // 2]
        if pd.notna(xnp):
            xcg = PARAMS["refs"]["Xref"]
            cref = PARAMS["refs"]["Cref"]
            sm = (xnp - xcg) / cref
            print(f"[ESTABILIDADE] Xnp: {xnp:.4f} | Margem Estática: {sm * 100:.2f}%")

    if "Cma" in df.columns:
        cma = df["Cma"].iloc[len(df) // 2]
        if pd.notna(cma):
            status = "ESTÁVEL" if cma < 0 else "INSTÁVEL"
            print(f"[ESTABILIDADE] Cma: {cma:.6f} ({status})")

    if "Cnb" in df.columns:
        cnb = df["Cnb"].iloc[len(df) // 2]
        if pd.notna(cnb):
            print(f"[LATERAL]      Cnb: {cnb:.6f} (Meta > 0)")

    print("-" * 55)
    print(f"[TRIMAGEM] (via ANGLE do canard - all-moving)")
    print(f" -> CL alvo:                {target_cl:.3f}")
    print(f" -> Incidência do canard:   {trim['canard_incidence_deg']:.3f}°")
    print(f" -> Alpha de equilíbrio:    {trim['alpha_trim_deg']:.3f}°")
    print(f" -> Cm final:               {trim['cm']:+.6f}")
    print("=" * 55)

    # atualiza PARAMS com o trim final (opcional)
    PARAMS["canard"]["incidence_deg"] = float(trim["canard_incidence_deg"])
    # regenera um .avl final já "trimado"
    avl_text_final = generate_avl_text(PARAMS)
    (out_dir / "aircraft_trimmed.avl").write_text(avl_text_final, encoding="utf-8")

    if PARAMS.get("show_geometry_in_xquartz", False):
        show_in_xquartz(PARAMS["avl_exe"], avl_file)

if __name__ == "__main__":
    main()