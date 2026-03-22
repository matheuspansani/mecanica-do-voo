# ✈️ Mecânica do Voo — Projeto de Aeronaves II

> **Universidade Federal de Uberlândia (UFU)** — Faculdade de Engenharia Mecânica  
> Curso de Engenharia Aeronáutica  
> Disciplina: **Projeto de Aeronaves II** — Módulo de Mecânica do Voo

---

## Sobre o Projeto

Este repositório contém as análises computacionais do módulo de **Mecânica do Voo** da disciplina de Projeto de Aeronaves II. O projeto consiste no estudo de um **caça canard-delta embarcado**, abrangendo:

- **Aerodinâmica** — varredura de ângulo de ataque, trimagem e polar de arrasto via AVL (Athena Vortex Lattice)
- **Estabilidade dinâmica** — cálculo dos modos longitudinais (período curto, fugóide) e laterais (Dutch Roll, convergência de rolamento, espiral) com análise de qualidades de voo (MIL-F-8785C)
- **Centro de gravidade** — distribuição de massas, passeio de CG para diferentes configurações de carga e diagrama de carregamento (_potato diagram_)

### Aeronave

| Parâmetro | Valor |
|---|---|
| Configuração | Canard-delta, embarcado |
| MTOW | ~30 400 kg |
| Envergadura | 11,72 m |
| Área de referência | 32,42 m² |
| MAC | 2,76 m |
| Motor | F135-PW-100 |
| Condição de cruzeiro | 30 000 ft, Mach 0,85 |

---

## Estrutura do Repositório

```
mecanica-do-voo/
│
├── avl_aerodinamica/            # Análise aerodinâmica (AVL)
│   ├── tri.py                   #   Sweep de alpha, trimagem por bisseção,
│   │                            #   geração do .avl e plots CL/CD/Cm
│   └── airfoils/                #   Perfis aerodinâmicos
│       └── NACA64A005.dat       #     Perfil da empenagem vertical
│
├── estabilidade_dinamica/       # Estabilidade dinâmica
│   └── dinamica.py              #   Matrizes de estado, autovalores,
│                                #   respostas temporais, qualidades de voo
│
├── cg_massas/                   # Centro de gravidade e massas
│   └── cg_analise.py            #   Distribuição de massas, passeio de CG,
│                                #   diagrama de carregamento (potato diagram)
│
├── requirements.txt             # Dependências Python
└── README.md
```

---

## Pré-requisitos

| Requisito | Versão mínima | Necessário para |
|---|---|---|
| Python | 3.10+ | Todos os scripts |
| AVL (Athena Vortex Lattice) | 3.40+ | `avl_aerodinamica/tri.py` |

### ⚠️ Instalação do AVL

O [AVL](https://web.mit.edu/drela/Public/web/avl/) (de Mark Drela, MIT) precisa estar instalado e acessível no `PATH` do sistema para rodar a análise aerodinâmica.

| SO | Comando |
|---|---|
| **macOS** (Homebrew) | `brew install avl` |
| **Linux** (Debian/Ubuntu) | `sudo apt install avl` ou baixe o binário em [web.mit.edu/drela/Public/web/avl](https://web.mit.edu/drela/Public/web/avl/) |
| **Windows** | Baixe o executável no link acima e adicione a pasta ao `PATH` |

Para verificar se está instalado:

```bash
avl
```

> Os módulos de estabilidade dinâmica e CG **não** dependem do AVL — apenas de Python + bibliotecas.

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/matheuspansani/mecanica-do-voo.git
cd mecanica-do-voo

# 2. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# 3. Instale todas as dependências de uma vez
pip install -r requirements.txt
```

---

## Como Executar

> Certifique-se de que o ambiente virtual está ativo (`source .venv/bin/activate`).

### 1. Análise Aerodinâmica (AVL)

```bash
cd avl_aerodinamica
python tri.py
```

Gera:
- Arquivo `.avl` da geometria
- Varredura CL(α), CD(α), Cm(α)
- Trimagem por bisseção do ângulo do canard
- CSVs e gráficos em `outputs/`

> ⚠️ **Requer AVL instalado no sistema.**

### 2. Estabilidade Dinâmica

```bash
cd estabilidade_dinamica
python dinamica.py
```

Gera:
- Matrizes de estado A (longitudinal e latero-direcional)
- Autovalores e parâmetros modais (ωn, ζ, T)
- Avaliação de qualidades de voo (MIL-F-8785C Classe IV)
- Respostas temporais e mapa de autovalores
- Arquivos em `outputs_dynamic/`

### 3. Distribuição de Massas e CG

```bash
cd cg_massas
python cg_analise.py
```

Gera:
- Plot da distribuição de massas sobre a silhueta da aeronave
- Passeio de CG vs. fração de combustível (múltiplas configurações)
- Diagrama de carregamento (_potato diagram_)
- Tabela resumo de margens estáticas
- Arquivos em `outputs_dynamic/`

---

## Autor

- **Matheus Pansani Rodrigues**

---

## Licença

Projeto acadêmico — UFU, 2026.
