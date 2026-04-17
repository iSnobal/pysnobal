# iPySnobal Codebase Analysis

> **Purpose:** This document provides a thorough investigation of the `ipysnobal` entry point and its underlying C code in the `iSnobal/pysnobal` repository. It is intended as a reference for GitHub Copilot Codebase Context agents and developers working on or reasoning about the distributed snowmelt model.

---

## Table of Contents

1. [Repository Structure](#1-repository-structure)
2. [Entry Points](#2-entry-points)
3. [Core Modules and Responsibilities](#3-core-modules-and-responsibilities)
4. [Data Flow](#4-data-flow)
5. [Dependencies](#5-dependencies)
6. [Call-Chain Documentation](#6-call-chain-documentation)
7. [C Macros and Global Variables](#7-c-macros-and-global-variables)
8. [Error Handling](#8-error-handling)

---

## 1. Repository Structure

Files and directories relevant to `ipysnobal` (the spatially-distributed, grid-capable path).

```
pysnobal/
├── ipysnobal.py               # Python helpers: get_timestep_info, initialize
├── pysnobal.py                # run_snobal entry, calls snobal.do_tstep_grid
├── defaults.py                # timestep constants, output name mappings
├── utils.py                   # unit converters (min2sec, C_TO_K)
└── c_snobal/
    ├── __init__.py            # exposes snobal extension: `from . import snobal`
    ├── snobal.pyx             # Cython binding (do_tstep_grid, do_tstep)
    ├── h/
    │   ├── pysnobal.h         # Python/C boundary structs: OUTPUT_REC, INPUT_REC_ARR, PARAMS
    │   ├── snobal.h           # Public C API + global variable declarations
    │   ├── envphys.h          # Physical constants, thermodynamic macros
    │   ├── snow.h             # Snow-specific macros (KTS, MELT, H2O_LEFT, …)
    │   ├── radiation.h        # STEF_BOLTZ, Planck constants
    │   └── types.h            # TRUE/FALSE, bool_t
    └── libsnobal/
        ├── call_snobal.c      # OpenMP-parallel per-cell bridge
        ├── do_data_tstep.c
        ├── _divide_tstep.c
        ├── _do_tstep.c
        ├── _e_bal.c
        ├── _mass_bal.c
        ├── init_snow.c
        ├── _calc_layers.c
        ├── _adj_layers.c
        ├── _layer_mass.c
        ├── _adj_snow.c
        ├── _snowmelt.c
        ├── _runoff.c
        ├── _precip.c
        ├── _time_compact.c
        ├── _h2o_compact.c
        ├── _evap_cond.c
        ├── _net_rad.c
        ├── _advec.c
        ├── _h_le.c
        ├── hle1.c             # Turbulent heat flux (Brutsaert 1982)
        ├── sati.c             # Saturation vapor pressure (ice)
        ├── satw.c             # Saturation vapor pressure (water)
        ├── g_snow.c           # Conductive heat between snow layers
        ├── g_soil.c           # Conductive heat from soil to snow
        ├── new_tsno.c         # New snow layer temperature
        ├── heat_stor.c        # Heat storage calculation
        ├── vars.c             # Public global variable definitions
        ├── _vars.c            # Private global variable definitions
        ├── _snobal.h          # Private function prototypes + private globals
        ├── _extern.h          # Legacy IPW extern declarations (not active)
        ├── _envphys.h         # Private stability functions
        └── error_logging.h    # LOG_ERROR macro
setup.py                       # Builds pysnobal.c_snobal.snobal extension
pyproject.toml                 # Project metadata, scripts entry points
```

---

## 2. Entry Points

### CLI

`ipysnobal` has **no dedicated CLI** registered in `pyproject.toml`. 
Only the point execution `pysnobal` CLI is registered:

```toml
# pyproject.toml L28-30
[project.scripts]
pysnobal = "pysnobal.pysnobal:run_pysnobal"
```

### Importable Python module

`ipysnobal` is a helper module, consumed by callers that construct the grid-run pipeline:

```python
# pysnobal/ipysnobal.py
from pysnobal.ipysnobal import get_timestep_info, initialize
```

### C-extension binding

The Cython extension `pysnobal.c_snobal.snobal` is the compute entry point:

```python
# pysnobal/c_snobal/__init__.py
from . import snobal

# calling convention (pysnobal/pysnobal.py L77-79)
from pysnobal.c_snobal import snobal
rt = snobal.do_tstep_grid(
    input1, input2, output_rec, timestep_info, mh, params, first_step=is_first
)
```

`do_tstep_grid` is defined in `snobal.pyx` at line 201. It calls into C via `call_snobal` (declared in `pysnobal.h` L133).

---

## 3. Core Modules and Responsibilities

### `pysnobal/ipysnobal.py`

| Function | Signature | Responsibility |
|---|---|---|
| `get_timestep_info` | `(options, config) → (params, timestep_info)` | Parses model options; builds the 4-element timestep records (data/normal/medium/small) with durations, intervals, mass thresholds, and output flags. Also opens the optional output file. |
| `initialize` | `(init) → output_rec` | Allocates `output_rec`: a dict of 2D NumPy float/int arrays (grid-shaped), seeded with values from `init`. This is the model state that persists between timesteps. |

Key constant sources referenced from `defaults.py`:

- `DATA_TIMESTEP=0`, `NORMAL_TIMESTEP=1`, `MEDIUM_TIMESTEP=2`, `SMALL_TIMESTEP=3`
- `WHOLE_TIMESTEP=0x1`, `DIVIDED_TIMESTEP=0x2`
- `DEFAULT_PARAMS`: default mass thresholds (60/10/1 kg/m²), timestep durations (60/15/1 min), `max_h2o_vol=0.01`, `max_z_s_0=0.25`.

### `pysnobal/c_snobal/snobal.pyx`

| Function | Signature | Responsibility |
|---|---|---|
| `do_tstep_grid` | `(input1, input2, output_rec, tstep_rec, mh, params, first_step=1, nthreads=1) → int` | **Primary grid path.** Marshals Python/NumPy data into C-compatible flat pointer structures, forwards them to `call_snobal`, then remaps output C arrays back to NumPy. |
| `do_tstep` | `(input1, input2, output_rec, tstep_rec, mh, params, first_step=True) → bool` | **Legacy per-pixel path.** Iterates each `(i,j)` grid cell manually in Python, setting C globals directly and calling `do_data_tstep` per cell. Single-threaded. |

### `libsnobal/call_snobal.c`

OpenMP-parallel bridge between the Cython/Python layer and the libsnobal engine. For each unmasked grid cell `n`:
1. Copies array element `n` into C globals.
2. Calls `init_snow()`.
3. Computes air pressure via `HYSTAT`.
4. Calls `do_data_tstep()`.
5. Writes modified globals back to output arrays.
6. Always returns `-1` (success sentinel used by Python).

### `libsnobal/do_data_tstep.c`

Runs one full data timestep (between `input_rec1` and `input_rec2`):
- Copies `input_rec1` into running climate globals.
- Computes per-level linear deltas from `input_rec2 - input_rec1`.
- Parses precipitation into rain/snow/depth.
- Resets `computed[]` flags.
- Delegates to `_divide_tstep(tstep_info[DATA_TSTEP])`.

### `libsnobal/_divide_tstep.c`

Recursive timestep subdivider:
- Computes next-level deltas and precip once (`computed[level]` guard).
- For each sub-interval: if mass is below threshold and level is not `SMALL_TSTEP`, recurse; otherwise call `_do_tstep`.

### `libsnobal/_do_tstep.c`

Single model timestep execution:
- Sets `time_step` and per-level precip state.
- Calls `_e_bal()` (energy balance), returns FALSE on error.
- Calls `_mass_bal()` (mass balance).
- Updates time-weighted running averages (`TIME_AVG` macro) and cumulative sums.
- Advances `current_time`, `time_since_out`.
- Steps climate inputs forward by `input_deltas[level]`.

### `libsnobal/_e_bal.c`

Computes point energy balance:
- `_net_rad()`: net allwave radiation `R_n = S_n + ε*(I_lw - σ*T_s_0^4)`.
- `_h_le()`: turbulent sensible (`H`) and latent (`L_v_E`) heat fluxes via `hle1`.
- `g_soil` / `g_snow`: conductive heat transfer from soil / between layers.
- `_advec()`: advected heat `M` from precipitation.
- Sums to `delta_Q_0` and `delta_Q`.

### `libsnobal/_mass_bal.c`

Computes point mass balance and updates snow temperatures:
- `_time_compact()`: density increase from temperature and overburden metamorphism.
- `_precip()`: adds precipitation to the snowpack or creates a new snowpack.
- `_snowmelt()`: melt or refreezing; adjusts `cc_s`, `h2o_total`, snowpack depth.
- `_evap_cond()`: surface and soil evaporation/condensation; adjusts `E_s`.
- `_h2o_compact()`: density increase from liquid water addition.
- `_runoff()`: computes `ro_predict`; removes excess water from snowpack.
- Solves for new snow temperatures via `new_tsno` or isothermal clamp.

### `libsnobal/init_snow.c`

Initializes (or re-normalizes) the snowpack state from globals `z_s`, `rho`, `T_s*`, `h2o_sat`:
- `_calc_layers()`: determines layer count (0, 1, or 2) and depths.
- `_layer_mass()`: per-layer specific mass from depth × density.
- `_cold_content()`: cold content per layer.
- Water content accounting (`h2o_vol`, `h2o_max`, `h2o`).

---

## 4. Data Flow

```
Python caller (run_snobal or notebook)
    │
    ├── Provides:
    │     input1, input2     dict of 2D NumPy arrays (per climate variable per cell)
    │     output_rec         dict of 2D NumPy arrays (model state)
    │     timestep_info      list[4] of timestep dicts
    │     mh                 dict { z_u, z_t, z_g }
    │     params             dict { relative_heights, max_h2o_vol, max_z_s_0 }
    │     first_step         int (0 based)
    │     nthreads           int (OpenMP threads)
    │
    ▼
do_tstep_grid()              [snobal.pyx L201]
    │  Loads tstep_info[0..3] into C globals
    │  Converts NumPy arrays → contiguous float64/int32 buffers
    │  Builds INPUT_REC_ARR and OUTPUT_REC_ARR struct of pointers
    │
    ▼
call_snobal(N, nthreads, first_step, tstep_info, &in1, &in2, params, &out1)
    │                         [call_snobal.c L18]
    │  [OpenMP parallel for, dynamic chunks of 100]
    │  For each unmasked cell n=0..N-1:
    │    ← load globals from arrays (climate, state, accumulators)
    │    → init_snow()
    │    → P_a = HYSTAT(...)
    │    → do_data_tstep()
    │    → write globals back to arrays
    │
    ▼
do_data_tstep()              [do_data_tstep.c L78]
    │  climate globals ← input_rec1
    │  input_deltas[DATA] = input_rec2 - input_rec1
    │  precip_info[DATA] ← m_pp/percent_snow/rho_snow derived
    │  computed[1..3] = FALSE
    │
    ▼
_divide_tstep(data_tstep)    [_divide_tstep.c L43]
    │  For each sub-interval:
    │    if (below_threshold && not SMALL_TSTEP) → recurse
    │    else → _do_tstep(next_lvl_tstep)
    │
    ▼
_do_tstep(tstep)             [_do_tstep.c L101]
    │  _e_bal()   → R_n, H, L_v_E, G, G_0, M, delta_Q, delta_Q_0
    │  _mass_bal() → updates rho, z_s*, T_s*, m_s*, cc_s*, h2o*, ro_predict
    │  Running averages updated (R_n_bar, H_bar, …)
    │  time_since_out, current_time advanced
    │  Climate vars stepped forward by input_deltas
    │
    ▼
Returns to do_tstep_grid()   [snobal.pyx L464]
    If rt != -1: raise error
    Else: remap C pointer arrays → NumPy arrays into output_rec
    Return rt  (=-1 on success)
```

---

## 5. Dependencies

### Build-time

| Dependency | Purpose |
|---|---|
| `cython` | Compiles `snobal.pyx` to C |
| `numpy<1.23` | Array type declarations in Cython (`cimport numpy`) |
| `setuptools`, `wheel` | Extension packaging |
| OpenMP (`-fopenmp` / `-lomp`) | Parallel per-cell loop in `call_snobal.c` |

### Runtime (ipysnobal path only)

| Dependency | Purpose |
|---|---|
| `numpy` | Input/output array containers |
| `pysnobal.defaults` | Constants: timestep levels, thresholds, variable-name maps |
| `pysnobal.utils` | `min2sec()` unit conversion |
| `pysnobal.c_snobal.snobal` | Compiled C-extension |

### C internal headers

| Header | What it provides |
|---|---|
| `snobal.h` | Public API: `init_snow`, `do_data_tstep`; all public globals; `TSTEP_REC`/`INPUT_REC` typedefs; timestep and output flag constants |
| `_snobal.h` | Private function prototypes; `PRECIP_REC` typedef; `#pragma omp threadprivate` for private state |
| `pysnobal.h` | `OUTPUT_REC`, `OUTPUT_REC_ARR`, `INPUT_REC_ARR`, `PARAMS` structs; `call_snobal` prototype |
| `envphys.h` | Physical constants + key macros: `HYSTAT`, `SPEC_HUM`, `LH_VAP`, `LH_FUS`, `DIFFUS`, `EVAP` |
| `snow.h` | Snow macros: `KTS`, `MELT`, `H2O_LEFT`, `DRY_SNO_RHO`, `SNOW_EMISSIVITY` |
| `radiation.h` | `STEF_BOLTZ`, Planck constants |
| `types.h` | `TRUE`, `FALSE`, `bool_t` |
| `error_logging.h` | `LOG_ERROR(message, ...)` macro |

---

## 6. Call-Chain Documentation

Full execution chain, function by function:

### Layer 0 — Python orchestration

**`run_snobal()` [`pysnobal/pysnobal.py` L29]**
- Parses inputs: calls `_parse_inputs` to produce `forcing_data_df`, `mh`, `params`, `timestep_info`, `output_rec`.
- Loops over `forcing_pairs` (adjacent timestep data frames).
- Calls `snobal.do_tstep_grid(input1, input2, output_rec, timestep_info, mh, params, first_step=is_first)` for each pair.
- Raises `ValueError` if return value is not `-1`.

### Layer 1 — Cython bridge

**`do_tstep_grid(input1, input2, output_rec, tstep_rec, mh, params, first_step, nthreads)` [`snobal.pyx` L201]**
- **Args:** two forcing dicts of 2D NumPy float64 arrays, model state dict, 4-element timestep list, measurement height dict, params dict, first-step flag, thread count.
- **Returns:** `int` (-1 on success, other on failure).
- Loads `tstep_rec[0..3]` into C global `tstep_info[0..3]` [L221-230].
- Builds `PARAMS c_params` struct from `mh`/`params` dicts [L213-219].
- For each field in `output_rec` and both input dicts: `np.ascontiguousarray(..., dtype=np.float64/int32)` and stores pointer in `OUTPUT_REC_ARR`/`INPUT_REC_ARR` [L231-423].
- Calls `call_snobal(N, nthreads, first_step, tstep_info, &input1_c, &input2_c, c_params, &output1_c)` [L462].
- If `rt != -1` returns immediately (error).
- Remaps each C pointer back to a NumPy array and writes into `output_rec` fields [L467-505].

### Layer 2 — C parallel bridge

**`call_snobal(N, nthreads, first_step, tstep[4], *input1, *input2, params, *output1)` [`call_snobal.c` L18]**
- **Args:** cell count, thread count, first-step flag, 4-element `TSTEP_REC` array, two `INPUT_REC_ARR*`, `PARAMS`, `OUTPUT_REC_ARR*`.
- **Returns:** `-1` unconditionally (always).
- Optionally sets OMP thread count [L31-33].
- Copies `tstep[n]` → `tstep_info[n]` [L35-37].
- Copies `PARAMS` fields → global `z_u`, `z_T`, `z_g`, `relative_hts`, `max_z_s_0`, `max_h2o_vol` [L39-44].
- `#pragma omp parallel shared(...) copyin(tstep_info, z_u, z_T, z_g, relative_hts, max_z_s_0, max_h2o_vol)` — sets up thread-private copies of globals [L46-47].
- `#pragma omp for schedule(dynamic, 100)` — distributes cells [L49].
- Per unmasked cell: loads input/state globals, calls `init_snow()`, calls `HYSTAT(...)` to set `P_a`, calls `do_data_tstep()`, writes output globals back to arrays [L60-177].
- On first step, energy/mass accumulator globals are explicitly zeroed after `init_snow` [L114-122].

### Layer 3 — Data timestep driver

**`do_data_tstep(void)` [`do_data_tstep.c` L78]**
- **Returns:** `TRUE`/`FALSE`.
- Sets climate globals (`S_n`, `I_lw`, `T_a`, `e_a`, `u`, `T_g`) from `input_rec1` [L92-99].
- Computes `input_deltas[DATA_TSTEP].*` = `input_rec2.* - input_rec1.*` [L102-109].
- If `precip_now`: partitions `m_pp` into `m_snow`/`m_rain`/`z_snow` in `precip_info[DATA_TSTEP]`; sets temperature and saturation flags for snow/rain/mixed [L112-146].
- Clears `computed[NORMAL..SMALL]` [L149-150].
- Calls `_divide_tstep(data_tstep)` [L153].

### Layer 4 — Recursive timestep subdivision

**`_divide_tstep(tstep)` [`_divide_tstep.c` L43]**
- **Args:** pointer to current level's `TSTEP_REC`.
- **Returns:** `TRUE`/`FALSE`.
- `next_level = tstep->level + 1` [L57].
- If `!computed[next_level]`: scales down deltas and precip by `intervals` [L72-88]; sets `computed[next_level]=TRUE`.
- For `i = 0..intervals-1` [L95]:
  - If `(next_level != SMALL_TSTEP) && _below_thold(threshold)` → recurse [L97].
  - Else → `_do_tstep(next_lvl_tstep)` [L100].

**`_below_thold(threshold)` [`_below_thold.c` L40]**
- Returns 1 if any layer's mass is below `threshold`; 0 otherwise.

### Layer 5 — Single timestep computation

**`_do_tstep(tstep)` [`_do_tstep.c` L101]**
- Sets `time_step = tstep->time_step` [L103].
- If `precip_now`: loads per-level `m_precip`, `m_rain`, `m_snow`, `z_snow` from `precip_info[level]` [L106-110].
- Sets `h2o_total = 0`, `snowcover = (layer_count > 0)` [L112-116].
- Calls `_e_bal()` [L118]; returns `FALSE` on failure.
- Calls `_mass_bal()` [L122].
- Updates averages (`TIME_AVG`) and sums for `R_n_bar`, `H_bar`, `L_v_E_bar`, `G_bar`, `M_bar`, `delta_Q_bar`, `G_0_bar`, `delta_Q_0_bar`, `E_s_sum`, `melt_sum`, `ro_pred_sum` [L128-158].
- Advances `current_time += time_step` [L161].
- Steps climate vars: `S_n += input_deltas[level].S_n`, etc. [L164-171].

### Layer 6 — Energy balance

**`_e_bal(void)` [`_e_bal.c` L24]**
- If `snowcover`:
  - `_net_rad()` → `R_n = S_n + ε*(I_lw - σ*T_s_0⁴)`.
  - `_h_le()` → `H`, `L_v_E`, `E` (returns FALSE on error).
  - `G`, `G_0` via `g_soil`/`g_snow`.
  - `_advec()` → `M`.
  - `delta_Q_0 = R_n + H + L_v_E + G_0 + M`.
  - `delta_Q = delta_Q_0 + G - G_0` (two-layer) or `= delta_Q_0` (one-layer).
- Else: zeroes all energy terms.

**`_h_le(void)` [`_h_le.c` L19]**
- Computes saturation vapor pressures `e_s = sati(T_s_0)`, `sat_vp = sati(T_a)` [L31-36].
- Clips `e_a` to `sat_vp` [L38-41].
- Adjusts measurement heights for relative vs. absolute mode [L44-49].
- Calls `hle1(P_a, T_a, T_s_0, rel_z_T, e_a, e_s, rel_z_T, u, rel_z_u, z_0, &H, &L_v_E, &E)` [L53].
- Returns FALSE if `hle1_result.return_code != 0`.

**`hle1(...)` [`hle1.c` L79]**  
Turbulent heat flux solver (Brutsaert 1982, iterative Obukhov length method, max 50 iterations):
- Validates inputs (heights, temperatures, pressures) [L118-148].
- Computes neutral-stability starting values [L181-184].
- Iterates Obukhov stability length `lo` and `psi`-function corrections until convergence (threshold `1e-5`) or `MAX_ITERATIONS` [L190-219].
- Returns `LoopResult { return_code=0 (success) or -1 (no converge) or -2 (bad input), remainder }`.

### Layer 6 — Mass balance sub-chain

**`_mass_bal(void)` [`_mass_bal.c` L25]**
Sequence (all mutate globals):
1. `_time_compact()` — gravitational and thermal compaction.
2. `_precip()` — adds snow/rain to pack or creates new pack via `init_snow`.
3. `_snowmelt()` — melt/refreeze, adjusts `cc_s`, `h2o_total`.
4. `_evap_cond()` — evaporation/condensation from surface and soil.
5. `_h2o_compact()` — compaction from liquid H₂O addition.
6. `_runoff()` — computes `ro_predict`, removes excess H₂O.
7. Solves new temperatures: `T_s_0 = new_tsno(m_s_0, T_s_0, cc_s_0)`, etc. [L57-70].

---

## 7. C Macros and Global Variables

### Key macros

#### Timestep level constants (`snobal.h` L107-124)

```c
#define DATA_TSTEP    0
#define NORMAL_TSTEP  1
#define MEDIUM_TSTEP  2
#define SMALL_TSTEP   3
#define WHOLE_TSTEP   0x1   // output when timestep is NOT subdivided
#define DIVIDED_TSTEP 0x2   // output when timestep IS subdivided
```

Used as indices into `tstep_info[]` throughout `do_data_tstep`, `_divide_tstep`, `_calc_layers`.

#### `TIME_AVG` (`_do_tstep.c` L98)

```c
#define TIME_AVG(avg, total_time, value, time_incr) \
    (((avg)*(total_time) + (value)*(time_incr)) / ((total_time)+(time_incr)))
```

Running time-weighted average, applied to all energy flux bars (`R_n_bar`, `H_bar`, etc.).

#### `HYSTAT` (`envphys.h` L213-216)

```c
#define HYSTAT(pb, tb, L, h, g, m)  /* hydrostatic air pressure */
```

Converts site elevation to air pressure `P_a`. Called once per cell in `call_snobal` [L128-135].

#### `MELT(Q)` (`snow.h` L40)

```c
#define MELT(Q)  ((Q) / LH_FUS(FREEZE))
```

Converts available energy to melt mass. Used in `_snowmelt.c`.

#### `H2O_LEFT(d, rhos, sat)` (`snow.h` L90-91)

```c
#define H2O_LEFT(d, rhos, sat) \
    ((sat * d * RHO_W0 * (RHO_ICE - rhos)) / RHO_ICE)
```

Maximum liquid water a snowpack can hold. Used in `init_snow`, `_runoff`, `_precip`.

#### `DRY_SNO_RHO(rhos, sat)` (`snow.h` L100-101)

Dry snow density (excluding liquid water). Used in `init_snow`.

#### `SPEC_HUM`, `GAS_DEN`, `DIFFUS`, `EVAP` (`envphys.h`)

Thermodynamic transforms used in `_evap_cond`, `_h_le`, `_advec`.

#### `LH_VAP`, `LH_FUS` (`envphys.h` L290, L297)

Latent heats. Temperature-dependent. Used in `_snowmelt`, `hle1`.

#### `LOG_ERROR(message, ...)` (`error_logging.h` L8)

```c
#define LOG_ERROR(message, ...) \
    fprintf(stderr, "[%s:%d] ERROR: " message "\n", __FILE__, __LINE__, ##__VA_ARGS__)
```

Non-fatal error logger to stderr.

#### `MAX_SNOW_DENSITY = 600` (`_adj_snow.c` L41)

Maximum snow density cap. Density is clipped and depth recalculated if exceeded.

#### `RMX = 550` (`_time_compact.c` L106)

Maximum density for time-compaction effects.

#### `MAX_DENSITY = 550`, `B = 0.4` (`_h2o_compact.c` L59, 64)

Parameters for H₂O compaction half-saturation function `Δρ = A / (1 + B/h2o_added)`.

### Global variables

All public globals declared in `snobal.h` L90-274 and **defined** in `vars.c`. Private globals declared in `_snobal.h` L43-64 and defined in `_vars.c`.

#### Execution state

| Variable | Type | Description | Set in | Consumed in |
|---|---|---|---|---|
| `tstep_info[4]` | `TSTEP_REC[]` | Level, duration, intervals, threshold, output flag | `call_snobal` [L36]; Python via `do_tstep_grid` [L221] | `do_data_tstep`, `_divide_tstep`, `_calc_layers` |
| `time_step` | `double` | Current sub-timestep length (sec) | `_do_tstep` [L103] | `_e_bal`, `_snowmelt`, `_evap_cond`, `_time_compact` |
| `current_time` | `double` | Model time (sec since start) | `call_snobal` [L60]; `_do_tstep` [L161] | `do_data_tstep` |
| `time_since_out` | `double` | Time since last output (sec) | `call_snobal` [L61]; `_do_tstep` [L142,157] | `_do_tstep` |

#### Climate forcing

| Variable | Type | Description |
|---|---|---|
| `input_rec1`, `input_rec2` | `INPUT_REC` | Boundary forcing records (S_n, I_lw, T_a, e_a, u, T_g, ro) |
| `S_n`, `I_lw`, `T_a`, `e_a`, `u`, `T_g`, `ro` | `double` | Current-step interpolated forcing values |
| `input_deltas[4]` | `INPUT_REC[]` | Per-level linear interpolation increments |

#### Measurement heights / parameters

| Variable | Description |
|---|---|
| `z_u` | Wind measurement height (m) |
| `z_T` | Air temp/vapor pressure measurement height (m) |
| `z_g` | Soil temperature measurement depth (m) |
| `z_0` | Roughness length (m) |
| `relative_hts` | 1 if heights are above snow surface; 0 if above ground |
| `max_h2o_vol` | Max liquid water as volume fraction (default 0.01) |
| `max_z_s_0` | Max surface layer thickness (default 0.25 m) |
| `P_a` | Air pressure (Pa), derived from elevation via `HYSTAT` |

#### Snowpack state

| Variable | Type | Description |
|---|---|---|
| `layer_count` | `int` | Number of layers: 0, 1, or 2 |
| `z_s`, `z_s_0`, `z_s_l` | `double` | Total, surface, lower layer depths (m) |
| `rho` | `double` | Average density (kg/m³) |
| `m_s`, `m_s_0`, `m_s_l` | `double` | Specific masses per layer (kg/m²) |
| `T_s`, `T_s_0`, `T_s_l` | `double` | Average, surface, lower temperatures (K) |
| `cc_s`, `cc_s_0`, `cc_s_l` | `double` | Cold contents (J/m²) |
| `h2o_sat` | `double` | Fractional liquid water saturation [0–1] |
| `h2o_vol` | `double` | Volumetric liquid water ratio |
| `h2o`, `h2o_max` | `double` | Actual and maximum liquid water (kg/m²) |
| `h2o_total` | `double` | Total liquid water: snowcover + melt + rain (kg/m²) |

#### Precipitation

| Variable | Type | Description |
|---|---|---|
| `precip_now` | `int` | 1 if precipitation is occurring |
| `m_pp`, `percent_snow`, `rho_snow`, `T_pp` | `double` | Raw precipitation inputs |
| `T_rain`, `T_snow`, `h2o_sat_snow` | `double` | Derived precipitation temperature/saturation |
| `m_precip`, `m_rain`, `m_snow`, `z_snow` | `double` | Per-timestep precipitation partition |
| `precip_info[4]` | `PRECIP_REC[]` | Per-level precipitation split (private) |

#### Energy balance

| Variable | Description |
|---|---|
| `R_n` | Net all-wave radiation (W/m²) |
| `H` | Sensible heat flux (W/m²) |
| `L_v_E` | Latent heat flux (W/m²) |
| `G`, `G_0` | Conductive heat from soil / between layers (W/m²) |
| `M` | Advected heat from precipitation (W/m²) |
| `delta_Q`, `delta_Q_0` | Energy change for pack / active layer (W/m²) |
| `R_n_bar`, …, `delta_Q_0_bar` | Time-weighted running averages of above |

#### Mass balance

| Variable | Description |
|---|---|
| `melt` | Specific melt (kg/m²) |
| `E` | Evaporative mass flux (kg/m²/s) |
| `E_s` | Total evaporation mass (kg/m²) |
| `ro_predict` | Predicted runoff (m/s) |
| `melt_sum`, `E_s_sum`, `ro_pred_sum` | Accumulated since last output |

#### Private control flags

| Variable | Description | Set in | Used in |
|---|---|---|---|
| `computed[4]` | Marks if level's deltas/precip are computed | `do_data_tstep` (reset) [L149]; `_divide_tstep` [L88] | `_divide_tstep` [L71] |
| `snowcover` | 1 if snow existed at start of timestep | `_do_tstep` [L115] | `_e_bal`, `_snowmelt`, `_h2o_compact`, `_runoff`, `_evap_cond`, `_time_compact` |
| `isothermal` | 1 if snowpack is at 0°C throughout | `_snowmelt` [L146-151] | `_mass_bal` temperature update [L64] |

#### OpenMP threadprivate declarations

All model globals (climate state, snowpack state, energy/mass fluxes, control flags) are declared `#pragma omp threadprivate` so each OpenMP thread maintains an independent copy when processing different grid cells in parallel.

See: `snobal.h` L275-281, `_snobal.h` L66, `do_data_tstep.c` L81-85.

---

## 8. Error Handling

### C-level

| Pattern | Location | Behavior |
|---|---|---|
| Return `FALSE` (0) | `do_data_tstep`, `_e_bal`, `_h_le`, `_evap_cond`, `_do_tstep`, `_divide_tstep` | Propagates failure up the call chain |
| `LOG_ERROR(...)` then continue | `call_snobal.c` L141 | Logs per-pixel failure to stderr; does **not** abort the parallel loop |
| `LOG_ERROR(...)` then return error code | `hle1.c` L119-147, `_h_le.c` L55-67 | Returns `LoopResult.return_code = -2` |
| `LOG_ERROR(...)` then `exit(EXIT_FAILURE)` | `sati.c` L17-18, `satw.c` L17-18, `hle1.c` L67-68 | Fatal termination for impossible inputs (temperature ≤ 0 K, invalid PSI type) |
| No return check | `_do_tstep.c` L122 (`_mass_bal()`) | `_mass_bal` return value is ignored |
| `call_snobal` unconditional return | `call_snobal.c` L182 | Always returns `-1`; C-level per-cell errors are only logged, never escalated |

### Python/Cython-level

| Pattern | Location | Behavior |
|---|---|---|
| `if rt != -1: raise ValueError` | `pysnobal.py` L82-83 | Single check: if `call_snobal` returns anything other than `-1`, raises exception |
| `abort()` on C error | `snobal.pyx` L622-627 | Legacy `do_tstep` path only — aborts process if `do_data_tstep` returns 0 on a multi-cell grid |

### Propagation gaps / known issues

1. **C errors are silent at Python level.** Because `call_snobal` always returns `-1`, any per-cell C error (logged via `LOG_ERROR` to stderr) is invisible to Python code.
2. **`_mass_bal` return value is unused.** `_do_tstep` calls `_mass_bal()` without checking its return value. If `_evap_cond` returns `FALSE`, the failure is absorbed.
3. **Fatal exits bypass Python.** `exit()` calls in `sati`, `satw`, and `hle1` terminate the process without a Python exception, which prevents clean error handling in calling code.
