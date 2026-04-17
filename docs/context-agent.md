# PySnobal — Codebase State (Context Agent)

## Repository Overview

**`iSnobal/pysnobal`** wraps the Snobal (1D point) and iSnobal (2D spatially distributed) snow mass and energy-balance models in Python. The repository contains:

- A **Cython bridge** (`snobal.pyx`) connecting Python to the C physics library.
- A **C physics library** (`libsnobal/`) implementing the Snobal snow model.
- A **point-scale Python API** (`pysnobal.py`) for single-location runs.
- A **spatial Python infrastructure** (`ipysnobal.py`) for distributed grid runs.

> **Naming conventions (from README):**
> - *Snobal* — 1D point model (C)
> - *iSnobal* — 2D image/grid model (C), running Snobal at every pixel
> - *PySnobal* — Python wrapper for the Snobal point model
> - *iPySnobal* — Python wrapper for the iSnobal spatial model (primary path is via [AWSM](https://github.com/iSnobal/awsm))

---

## Directory Layout

```
pysnobal/
├── pysnobal/
│   ├── c_snobal/
│   │   ├── snobal.pyx          # Cython bridge — exposes C functions to Python
│   │   ├── h/                  # Public C headers
│   │   │   ├── snobal.h        # Core snobal public API + all global state
│   │   │   └── pysnobal.h      # Struct defs for Python/C interface layer
│   │   └── libsnobal/          # C physics library
│   │       ├── call_snobal.c   # Grid-parallel entry point (OpenMP)
│   │       ├── do_data_tstep.c # Per-pixel data-timestep driver
│   │       ├── init_snow.c     # Snowpack initialiser
│   │       ├── _divide_tstep.c # Recursive adaptive-timestep subdivider
│   │       ├── _do_tstep.c     # Single-timestep physics integrator
│   │       ├── _e_bal.c        # Energy balance
│   │       ├── _mass_bal.c     # Mass balance
│   │       └── … (other physics files)
│   ├── pysnobal.py             # Point-scale Python API (PySnobal)
│   ├── ipysnobal.py            # Spatial-scale Python infrastructure (iPySnobal)
│   ├── defaults.py             # All constants, defaults, and name mappings
│   └── utils.py                # Minimal helpers (C_TO_K = 273.16, min2sec)
├── config/config.yaml          # Annotated template configuration file
├── notebooks/                  # Example Jupyter notebooks
├── tests/                      # pytest suite
├── setup.py
└── pyproject.toml
```

---

## 1. C Physics Library (`libsnobal/`)

### Global State Model

The C library is entirely **global-state-driven**. Every physical quantity is a `#pragma omp threadprivate` C global, which enables safe OpenMP parallelism across pixels. Key variable groups defined in `snobal.h`:

| Group | Key Variables |
|-------|---------------|
| Snowpack state | `z_s`, `rho`, `T_s`, `T_s_0`, `T_s_l`, `cc_s`, `cc_s_0`, `cc_s_l`, `h2o_sat`, `h2o`, `h2o_vol`, `h2o_max`, `h2o_total`, `m_s`, `m_s_0`, `m_s_l`, `layer_count` |
| Climate inputs (current tstep) | `S_n`, `I_lw`, `T_a`, `e_a`, `u`, `T_g`, `ro` |
| Input records (start/end of data tstep) | `INPUT_REC input_rec1`, `input_rec2` |
| Energy balance averages | `R_n_bar`, `H_bar`, `L_v_E_bar`, `G_bar`, `G_0_bar`, `M_bar`, `delta_Q_bar`, `delta_Q_0_bar` |
| Mass balance sums | `melt_sum`, `E_s_sum`, `ro_pred_sum` |
| Timestep config | `TSTEP_REC tstep_info[4]` (levels: DATA=0, NORMAL=1, MEDIUM=2, SMALL=3) |
| Measurement heights / params | `z_u`, `z_T`, `z_g`, `z_0`, `relative_hts`, `max_h2o_vol`, `max_z_s_0` |
| Precipitation | `m_pp`, `percent_snow`, `rho_snow`, `T_pp`, `precip_now` |
| Timing | `current_time`, `time_since_out` |

### Public C API (2 functions — `snobal.h`)

```c
void init_snow(void);
// Derives layer structure, cold content, and water content from:
//   z_s, rho, T_s, T_s_0, T_s_l, h2o_sat, max_h2o_vol
// Sets: layer_count, m_s, m_s_0, m_s_l, cc_s, cc_s_0, cc_s_l,
//       h2o_vol, h2o_max, h2o, h2o_total

int do_data_tstep(void);
// Runs model for 1 data timestep between input_rec1 and input_rec2.
// Returns TRUE (1) on success, FALSE (0) on error.
```

### Grid Entry Point (`call_snobal.c`)

```c
int call_snobal(
    int N,                   // number of grid pixels
    int nthreads,            // OpenMP thread count
    int first_step,          // 1 = first timestep (zero EB accumulators)
    TSTEP_REC tstep[4],      // timestep hierarchy config
    INPUT_REC_ARR *input1,   // struct-of-arrays for start of data tstep
    INPUT_REC_ARR *input2,   // struct-of-arrays for end of data tstep
    PARAMS params,           // measurement heights + model params
    OUTPUT_REC_ARR *output1  // struct-of-arrays state (in + out)
);
// Returns -1 on success (yes, -1 is the "OK" sentinel throughout)
```

- Iterates over `N` pixels in an **OpenMP parallel for** loop (dynamic scheduling, chunk = 100).
- Each thread copies struct-of-array entries into thread-private globals, calls `init_snow()` then `do_data_tstep()`.
- Results are written back to `OUTPUT_REC_ARR`.

### Key C Structs (defined in `pysnobal.h`, mirrored in `snobal.pyx`)

| Struct | Purpose |
|--------|---------|
| `INPUT_REC` | Single-pixel climate inputs: `S_n`, `I_lw`, `T_a`, `e_a`, `u`, `T_g`, `ro` |
| `INPUT_REC_ARR` | Struct-of-arrays for the same fields plus precip: `m_pp`, `percent_snow`, `rho_snow`, `T_pp` |
| `OUTPUT_REC` | Single-pixel full state snapshot (31 `double`/`int` fields) |
| `OUTPUT_REC_ARR` | Struct-of-arrays of the same 31 fields |
| `PARAMS` | Measurement heights + model parameters: `z_u`, `z_T`, `z_g`, `relative_heights`, `max_h2o_vol`, `max_z_s_0` |
| `TSTEP_REC` | One timestep level: `level`, `time_step` (s), `intervals`, `threshold` (kg/m²), `output` flags |

### Adaptive Timestep Engine

```
do_data_tstep()
  ├─ Copy input_rec1 → current climate globals
  ├─ Compute input_deltas[DATA] = input_rec2 − input_rec1
  ├─ Decompose precip into rain/snow/mixed
  └─ _divide_tstep(data_tstep)  ← recursive
      ├─ Compute sub-level deltas (linear interpolation)
      └─ For each sub-interval:
          ├─ if mass < threshold AND not SMALL_TSTEP → recurse deeper
          └─ else → _do_tstep()
              ├─ _e_bal()    → delta_Q, delta_Q_0
              ├─ _mass_bal() → melt, runoff, E_s
              ├─ _precip()
              ├─ _runoff()
              └─ _adj_snow() / _adj_layers()
```

---

## 2. Cython Bridge (`snobal.pyx`)

Exposes two Python-callable functions. All physical arrays must be 2D (shape `(rows, cols)` or `(1, 1)` for point runs).

### `do_tstep_grid` (primary — grid-capable)

```python
def do_tstep_grid(
    input1,      # dict of 2D numpy arrays (climate forcing, start of tstep)
    input2,      # dict of 2D numpy arrays (climate forcing, end of tstep)
    output_rec,  # dict of 2D numpy arrays (snowpack state — mutated in-place)
    tstep_rec,   # list of 4 dicts matching TSTEP_REC fields
    mh,          # dict: {z_u, z_t, z_g}
    params,      # dict: {relative_heights, max_h2o_vol, max_z_s_0}
    first_step=1,
    nthreads=1
) -> int          # -1 = success; any other value = error
```

**Data flow inside `do_tstep_grid`:**
1. Pack Python dicts into `INPUT_REC_ARR` / `OUTPUT_REC_ARR` C structs using `np.ascontiguousarray` + `&arr[0,0]`.
2. Call `call_snobal(N, nthreads, first_step, tstep_info, &input1_c, &input2_c, c_params, &output1_c)`.
3. Write C pointer results back into `output_rec` using `np.PyArray_SimpleNewFromData`.

### `do_tstep` (legacy — scalar/loop variant)

Older implementation that iterates over pixels in Python. Not used by the current `pysnobal.py` point API.

---

## 3. Point-Scale Python API — `pysnobal.py`

Implements the **PySnobal point model**. All arrays are shape `(1, 1)`, representing a single geographic location.

### Public Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `load_config` | `(path: Path) → dict` | Load YAML config file |
| `run_snobal` | `(forcing_data_df, config, show_pbar=False) → pd.DataFrame` | **Primary entry point** |
| `run_pysnobal` | `() → None` | CLI entry point (parses args, calls `run_snobal`) |

### `run_snobal` Execution Flow

```
run_snobal(forcing_data_df, config)
  │
  ├─ _parse_inputs()
  │   ├─ _check_forcing_df()    # validate columns, uniform timestep, no NaNs
  │   ├─ _check_config()        # validate required sections; backfill defaults
  │   ├─ rename columns + convert °C → K
  │   ├─ build mh dict          # {z_t, z_g, z_u} from config["z"]
  │   ├─ build params dict      # {relative_heights, max_h2o_vol, max_z_s_0}
  │   ├─ build timestep_info[4] # list of TSTEP_REC-equivalent dicts
  │   └─ build output_rec       # dict of (1,1) numpy arrays; seeded from config["init"]
  │
  ├─ pre-build forcing_pairs dict   # {dt: (input1_dict, input2_dict)} for all pairs
  │
  └─ for each (dt, (input1, input2)):
      ├─ snobal.do_tstep_grid(input1, input2, output_rec, ...)
      │   └─ [Cython → C → libsnobal physics]
      ├─ assert return value == -1 (raise ValueError otherwise)
      └─ _append_output()    # harvest output_rec[key][0][0] scalars;
                              # reset output_rec["time_since_out"][0][0] = 0.0

return pd.DataFrame(running_output).set_index("Datetime")
```

### CLI Usage

Registered as the `pysnobal` console script in `pyproject.toml`:

```bash
pysnobal -c config/config.yaml [-o param.key=value ...]
```

Supports dot-notation overrides for any config key (e.g., `io.forcing_path=./data.csv`).

### YAML Config Schema

```yaml
io:
  forcing_path: <path to CSV>   # required
  output_path:  <path>          # required

z:
  air_temp_m:    2.33           # required; z_T (m)
  soil_temp_m:   1.0            # required; z_g (m)
  wind_speed_m:  2.5            # required; z_u (m)

params:
  elevation_m:         2000     # required
  roughness_length_m:  0.001    # required; z_0

init:                           # optional; default = zero snowpack
  snow_depth_m:              null   # z_s
  bulk_snow_density_kgm-3:   null   # rho
  active_layer_temp_degC:    null   # T_s_0
  avg_snow_temp_degC:        null   # T_s
  h2o_sat_%:                 null   # h2o_sat

defaults:                       # optional; all have built-in defaults
  relative_heights:              null   # False
  max_h2o_vol_frac:              null   # 0.01
  max_active_layer_thickness_m:  null   # 0.25 m
  normal_tstep_mass_thresh_kgm-2: null  # 60 kg/m²
  medium_tstep_mass_thresh_kgm-2: null  # 10 kg/m²
  small_tstep_mass_thresh_kgm-2:  null  # 1 kg/m²
  normal_tstep_min: null                # 60 min
  medium_tstep_min: null                # 15 min
  small_tstep_min:  null                # 1 min
```

### Forcing Data Format (CSV)

The CSV must have a datetime index and the following columns:

| Column Name | C Name | Unit |
|-------------|--------|------|
| `net_solar_Wm-2` | `S_n` | W/m² |
| `downwelling_thermal_Wm-2` | `I_lw` | W/m² |
| `temp_air_degC` | `T_a` | °C → K at boundary |
| `temp_ground_degC` | `T_g` | °C → K at boundary |
| `vapor_pressure_Pa` | `e_a` | Pa |
| `wind_speed_ms-1` | `u` | m/s |
| `precip_mass_mm` | `m_pp` | mm (kg/m²) |
| `precip_temp_degC` | `T_pp` | °C → K at boundary |
| `snow_precip_fraction` | `percent_snow` | 0–1 |
| `snow_precip_density_kgm-3` | `rho_snow` | kg/m³ |

### Output Variables

**Energy balance terms (`EM_OUT`):** `R_n_bar`, `H_bar`, `L_v_E_bar`, `M_bar`, `G_bar`, `G_0_bar`, `delta_Q_bar`, `delta_Q_0_bar`

**Snow state terms (`SNOW_OUT`):** `rho`, `T_s`, `T_s_0`, `T_s_l`, `z_s`, `z_s_0`, `z_s_l`, `cc_s`, `cc_s_0`, `cc_s_l`, `m_s`, `m_s_0`, `m_s_l`, `h2o`, `h2o_sat`, `E_s_sum`, `melt_sum`, `ro_pred_sum`

Temperature output columns have 273.16 K subtracted before returning (converted back to °C).

---

## 4. Spatial-Scale Python Infrastructure — `ipysnobal.py`

Implements helpers for the **iPySnobal spatial/image model**. Intended for running Snobal at every pixel of a 2D grid. The recommended production path is via [AWSM](https://github.com/iSnobal/awsm), which orchestrates iPySnobal inputs and configuration.

### `initialize(init) → dict`

Creates the `output_rec` state dictionary for a spatial grid run:

```python
sz = init["elevation"].shape   # full 2D grid shape (rows, cols)
s = {key: np.zeros(sz) for key in fields}
# Then overlays any pre-existing values from init
```

Fields initialised (35 total, all to zero then updated from `init`):
`E_s_sum`, `G_0_bar`, `G_bar`, `H_bar`, `L_v_E_bar`, `M_bar`, `R_n_bar`,
`T_s`, `T_s_0`, `T_s_l`, `cc_s`, `cc_s_0`, `cc_s_l`, `current_time`,
`delta_Q_0_bar`, `delta_Q_bar`, `elevation`, `h2o`, `h2o_max`, `h2o_sat`,
`h2o_total`, `h2o_vol`, `layer_count`, `m_s`, `m_s_0`, `m_s_l`, `mask`,
`melt_sum`, `rho`, `ro_pred_sum`, `time_since_out`, `z_0`, `z_s`, `z_s_0`, `z_s_l`

### `get_timestep_info(options, config) → (params, timestep_info)`

Parses an `options` dict (from AWSM/CLI-style configuration) into:
- `timestep_info[4]` — list of TSTEP_REC-equivalent dicts
- `params` dict — includes `stop_no_snow`, `temps_in_C`, `out_filename`, `out_file` (file handle) in addition to the standard model parameters

Key difference from `pysnobal.py`: this function supports richer output modes (`"data"`, `"normal"`, `"all"`) and file-based output — features needed for long spatial runs managed by AWSM.

---

## 5. Variable Name Mappings (`defaults.py`)

Three translation dictionaries bridge user-facing names and internal C names:

```python
FORCING_NAMES_CUSTOM2SNOBAL = {
    "net_solar_Wm-2": "S_n",
    "downwelling_thermal_Wm-2": "I_lw",
    "temp_air_degC": "T_a",
    "temp_ground_degC": "T_g",
    "vapor_pressure_Pa": "e_a",
    "wind_speed_ms-1": "u",
    "precip_mass_mm": "m_pp",
    "precip_temp_degC": "T_pp",
    "snow_precip_fraction": "percent_snow",
    "snow_precip_density_kgm-3": "rho_snow",
}

INIT_NAMES_CUSTOM2SNOBAL = {
    "snow_depth_m": "z_s",
    "bulk_snow_density_kgm-3": "rho",
    "active_layer_temp_degC": "T_s_0",
    "avg_snow_temp_degC": "T_s",
    "h2o_sat_%": "h2o_sat",
}

OUTPUT_NAMES_SNOBAL2CUSTOM = {
    "rho": "bulk_density_snow_kgm-3",
    "T_s_0": "temp_active_layer_degC",
    # … (26 entries total, see defaults.py)
}
```

---

## 6. Default Parameters

```python
DEFAULT_SNOWPACK = {
    "snow_depth_m": 0.0,
    "bulk_snow_density_kgm-3": 0.0,
    "active_layer_temp_degC": 0.0,   # stored as K internally
    "avg_snow_temp_degC": 0.0,
    "h2o_sat_%": 0.0,
}

DEFAULT_PARAMS = {
    "relative_heights": False,
    "max_h2o_vol_frac": 0.01,
    "max_active_layer_thickness_m": 0.25,
    "normal_tstep_mass_thresh_kgm-2": 60.0,
    "medium_tstep_mass_thresh_kgm-2": 10.0,
    "small_tstep_mass_thresh_kgm-2": 1.0,
    "normal_tstep_min": 60.0,
    "medium_tstep_min": 15.0,
    "small_tstep_min": 1.0,
}
```

---

## 7. Tests

All tests are in `tests/` and run via pytest:

- `test_config_loading.py` — YAML load and override logic
- `test_input_parsing.py` — forcing data validation and config checking
- `test_pysnobal_real_data.py` — end-to-end point model runs against expected output CSV
  - Two known-failing output columns (`inter_layer_heat_flux_Wm-2`, `delta_active_layer_energy_Wm-2`) are dropped from comparisons

---

## 8. Known Quirks and Gotchas

1. **`first_step` off-by-one**: The flag is set `int(i == 1)` in `pysnobal.py`, meaning it fires on the *second* iteration (index 1), not the first (index 0).
2. **Return value sentinel**: `call_snobal` and `do_tstep_grid` return **`-1` on success**. Any other value is an error. The Python caller raises `ValueError` if `rt != -1`.
3. **`output_rec` is mutable state**: passed by reference every timestep; serves as both the initial conditions input and the output sink. The snowpack state accumulates across the entire run.
4. **Temperature boundary**: All temperatures must be in **Kelvin** at the C/Cython boundary. `pysnobal.py` adds `273.16` on the way in and subtracts on the way out for temperature output columns.
5. **`time_since_out` manual reset**: After harvesting each timestep's output, `pysnobal.py` explicitly sets `output_rec["time_since_out"][0][0] = 0.0`.
6. **Point mode uses grid call**: The point API (`pysnobal.py`) calls `do_tstep_grid` with `(1, 1)` shaped arrays — it uses the same parallel grid path but with N=1.
