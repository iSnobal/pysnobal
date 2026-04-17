# PySnobal — Ecosystem Contracts (Ecosystem Agent)

## Purpose

This document defines the cross-repository contracts for `iSnobal/pysnobal`: the interfaces, data formats, and integration points that external systems must honour when calling into or depending on this library.

---

## 1. Package Identity

| Property | Value |
|----------|-------|
| Package name | `pysnobal` |
| PyPI / install name | `pysnobal` |
| CLI entry point | `pysnobal` → `pysnobal.pysnobal:run_pysnobal` |
| Python requirement | `>=3.9` |
| Build system | `setuptools` + Cython extension (`c_snobal/snobal.pyx`) |
| C compiler requirement | Must support OpenMP (`-fopenmp`) |

---

## 2. Importable Public API

### Point model (`pysnobal.pysnobal`)

```python
from pysnobal.pysnobal import load_config, run_snobal, run_pysnobal
```

| Symbol | Type | Contract |
|--------|------|----------|
| `load_config(path)` | function | Accepts `pathlib.Path` or `str`; returns `dict[str, Any]` from YAML |
| `run_snobal(forcing_data_df, config, show_pbar=False)` | function | Returns `pd.DataFrame` indexed by `Datetime`; raises `ValueError` on bad inputs or model errors |
| `run_pysnobal()` | function | CLI entry point; reads `sys.argv`; no return value |

### Spatial model infrastructure (`pysnobal.ipysnobal`)

```python
from pysnobal.ipysnobal import initialize, get_timestep_info
```

| Symbol | Type | Contract |
|--------|------|----------|
| `initialize(init)` | function | Accepts `dict` with `"elevation"` numpy array defining grid shape; returns `dict` of zero-initialised numpy arrays |
| `get_timestep_info(options, config)` | function | Returns `(params_dict, timestep_info_list)`; used by AWSM |

### Cython extension (`pysnobal.c_snobal.snobal`)

```python
from pysnobal.c_snobal import snobal
snobal.do_tstep_grid(input1, input2, output_rec, tstep_rec, mh, params, first_step, nthreads)
```

This is a **compiled extension** and must be built before import. It is **not** part of the stable public API intended for direct external use — call it through `pysnobal.pysnobal.run_snobal` instead.

---

## 3. Forcing Data Contract

External systems (e.g. AWSM, data pipelines) that provide forcing data to the **point model** must supply a `pd.DataFrame` with:

- A **datetime index** (timezone-naive, parseable by `pd.read_csv(..., parse_dates=True, index_col=0)`)
- A **uniform timestep** — validated; raises `ValueError` if non-uniform
- **No NaN values** in any required column — validated; raises `ValueError`
- **The following columns** (names are case-sensitive):

| Column Name | Unit | C Variable |
|-------------|------|------------|
| `net_solar_Wm-2` | W/m² | `S_n` |
| `downwelling_thermal_Wm-2` | W/m² | `I_lw` |
| `temp_air_degC` | °C | `T_a` |
| `temp_ground_degC` | °C | `T_g` |
| `vapor_pressure_Pa` | Pa | `e_a` |
| `wind_speed_ms-1` | m/s | `u` |
| `precip_mass_mm` | mm (kg/m²) | `m_pp` |
| `precip_temp_degC` | °C | `T_pp` |
| `snow_precip_fraction` | 0–1 | `percent_snow` |
| `snow_precip_density_kgm-3` | kg/m³ | `rho_snow` |

**Temperature conversion**: `pysnobal.py` internally adds 273.16 K before passing to C. Callers **must** supply temperatures in °C.

---

## 4. Configuration Contract

Any system generating a config dict (or YAML) for `run_snobal` must provide:

### Required sections

```yaml
io:
  output_path: <str>   # output CSV path

z:
  air_temp_m: <float>   # z_T  — height of air temp / vapor pressure sensor (m, positive)
  soil_temp_m: <float>  # z_g  — depth of soil temp sensor (m, positive)
  wind_speed_m: <float> # z_u  — height of wind sensor (m, positive)

params:
  elevation_m: <float>         # site elevation (m)
  roughness_length_m: <float>  # aerodynamic roughness length z_0 (m)
```

### Optional sections (with defaults)

```yaml
init:
  snow_depth_m: <float>              # default 0.0
  bulk_snow_density_kgm-3: <float>   # default 0.0
  active_layer_temp_degC: <float>    # default 0.0 °C
  avg_snow_temp_degC: <float>        # default 0.0 °C
  h2o_sat_%: <float>                 # default 0.0

defaults:
  relative_heights: <bool>                     # default False
  max_h2o_vol_frac: <float>                    # default 0.01
  max_active_layer_thickness_m: <float>        # default 0.25
  normal_tstep_mass_thresh_kgm-2: <float>      # default 60.0
  medium_tstep_mass_thresh_kgm-2: <float>      # default 10.0
  small_tstep_mass_thresh_kgm-2: <float>       # default 1.0
  normal_tstep_min: <float>                    # default 60.0
  medium_tstep_min: <float>                    # default 15.0
  small_tstep_min: <float>                     # default 1.0
```

**Validation**: `_check_config` raises `ValueError` for any missing required key or a negative instrument height.

---

## 5. Output Contract

`run_snobal` returns a `pd.DataFrame` with a `Datetime` index (same timezone/format as input) and the following output columns:

### Energy balance columns

| Column Name | Snobal variable | Unit |
|-------------|----------------|------|
| `net_radiation_Wm-2` | `R_n_bar` | W/m² |
| `sensible_heat_flux_Wm-2` | `H_bar` | W/m² |
| `latent_heat_flux_Wm-2` | `L_v_E_bar` | W/m² |
| `advective_heat_flux_Wm-2` | `M_bar` | W/m² |
| `ground_heat_flux_Wm-2` | `G_bar` | W/m² |
| `inter_layer_heat_flux_Wm-2` | `G_0_bar` | W/m² |
| `delta_snow_energy_Wm-2` | `delta_Q_bar` | W/m² |
| `delta_active_layer_energy_Wm-2` | `delta_Q_0_bar` | W/m² |

### Snow state columns

| Column Name | Snobal variable | Unit |
|-------------|----------------|------|
| `bulk_density_snow_kgm-3` | `rho` | kg/m³ |
| `temp_snow_degC` | `T_s` | °C |
| `temp_active_layer_degC` | `T_s_0` | °C |
| `temp_lower_layer_degC` | `T_s_l` | °C |
| `thickness_snow_m` | `z_s` | m |
| `thickness_active_layer_m` | `z_s_0` | m |
| `thickness_lower_layer_m` | `z_s_l` | m |
| `coldcontent_snow_Jm-2` | `cc_s` | J/m² |
| `coldcontent_active_layer_Jm-2` | `cc_s_0` | J/m² |
| `coldcontent_lower_layer_Jm-2` | `cc_s_l` | J/m² |
| `specific_mass_snow_kgm-2` | `m_s` | kg/m² |
| `specific_mass_active_layer_kgm-2` | `m_s_0` | kg/m² |
| `specific_mass_lower_layer_kgm-2` | `m_s_l` | kg/m² |
| `liquid_h2o_kgm-2` | `h2o` | kg/m² |
| `h2o_sat_%` | `h2o_sat` | 0–1 |
| `evap_kgm-2` | `E_s_sum` | kg/m² |
| `snowmelt_kgm-2` | `melt_sum` | kg/m² |
| `surface_Water_input_kg` | `ro_pred_sum` | kg |

**Temperature output**: All `*_degC` columns have 273.16 K subtracted; they are returned in °C.

> **Known issue**: `inter_layer_heat_flux_Wm-2` and `delta_active_layer_energy_Wm-2` show consistent small numerical errors vs. reference output; these columns are excluded from regression test comparisons.

---

## 6. Cython / C Boundary Contract

Systems that need to call the Cython layer directly (e.g. advanced spatial callers not going through AWSM):

### `do_tstep_grid` calling convention

```python
rt = snobal.do_tstep_grid(
    input1,      # dict[str, np.ndarray(shape=(M,N), dtype=float64)]
    input2,      # dict[str, np.ndarray(shape=(M,N), dtype=float64)]
    output_rec,  # dict[str, np.ndarray(shape=(M,N))] — MUTATED IN PLACE
    tstep_rec,   # list of 4 dicts: {level, output, threshold, time_step, intervals}
    mh,          # dict: {z_u: float, z_t: float, z_g: float}
    params,      # dict: {relative_heights: bool, max_h2o_vol: float, max_z_s_0: float}
    first_step=1,
    nthreads=1,
)
# rt == -1  →  success
# rt != -1  →  error occurred
```

### Input array key names

`input1` / `input2` must contain: `S_n`, `I_lw`, `T_a`, `e_a`, `u`, `T_g`, `m_pp`, `percent_snow`, `rho_snow`, `T_pp`

All temperature arrays must be in **Kelvin**.

### `output_rec` required keys

`mask` (`int32`), `elevation`, `z_0`, `z_s`, `z_s_0`, `z_s_l`, `rho`, `T_s_0`, `T_s_l`, `T_s`, `h2o_sat`, `h2o_max`, `h2o`, `h2o_vol`, `h2o_total`, `layer_count` (`int32`), `cc_s_0`, `cc_s_l`, `cc_s`, `m_s_0`, `m_s_l`, `m_s`, `R_n_bar`, `H_bar`, `L_v_E_bar`, `G_bar`, `G_0_bar`, `M_bar`, `delta_Q_bar`, `delta_Q_0_bar`, `E_s_sum`, `melt_sum`, `ro_pred_sum`, `current_time`, `time_since_out`

### `tstep_rec` structure

```python
tstep_rec = [
    {"level": 0, "output": 0x2, "threshold": None,  "time_step": <data_sec>,   "intervals": None},
    {"level": 1, "output": False, "threshold": 60.0, "time_step": 3600,         "intervals": <N>},
    {"level": 2, "output": False, "threshold": 10.0, "time_step": 900,          "intervals": 4},
    {"level": 3, "output": False, "threshold": 1.0,  "time_step": 60,           "intervals": 15},
]
```

Output flags: `0x1` = `WHOLE_TSTEP`, `0x2` = `DIVIDED_TSTEP`, `False`/`0` = no output.

---

## 7. AWSM Integration Contract

AWSM ([`iSnobal/awsm`](https://github.com/iSnobal/awsm)) is the recommended orchestrator for spatial iPySnobal runs. AWSM's contract with pysnobal:

- Calls `ipysnobal.initialize(init)` to build the spatial `output_rec` from a topo/DEM-shaped `init["elevation"]` array.
- Calls `ipysnobal.get_timestep_info(options, config)` to build `params` and `timestep_info` from its own options dict.
- Calls `snobal.do_tstep_grid(...)` directly with spatial (M×N) arrays.
- Manages the `output_rec` state dict across timesteps (persistent across calls).
- Sets `mask` values to 0 for pixels that should be skipped (no-data / outside watershed).

AWSM-specific `params` keys (not present in `pysnobal.py` point API):
- `stop_no_snow` — halt model if no snow remains
- `temps_in_C` — whether input temperatures are in °C (legacy flag)
- `out_filename` / `out_file` — file handle for writing output during run

---

## 8. Versioning and Build

- Version is managed via `setuptools_scm` (git tags); written to `pysnobal/version.py` at build time.
- The Cython extension (`snobal.pyx`) must be compiled before the package is usable; distributed via `setup.py` / the `setuptools` build backend.
- Build dependencies: `cython`, `numpy<1.23`, `setuptools`, `setuptools_scm`, `wheel`.
- Runtime dependencies: defined in `pyproject.toml` `dependencies = []` (currently empty — numpy, pandas, etc. are expected in the environment, e.g. via the iSnobal conda environment).

---

## 9. Error Handling Conventions

| Situation | Mechanism |
|-----------|-----------|
| Missing/malformed config key | `ValueError` raised by `_check_config` |
| Missing/NaN forcing column | `ValueError` raised by `_check_forcing_df` |
| Non-uniform forcing timestep | `ValueError` raised by `_check_forcing_df` |
| Model error in C | `do_data_tstep` returns `FALSE`; `call_snobal` logs via `LOG_ERROR`; `do_tstep_grid` returns a value other than -1; Python caller raises `ValueError` |
| Config override parse error | `ValueError` raised by `_override_config` |

---

## 10. Implicit Contracts (Non-obvious)

1. **Timestep input requires consecutive pairs**: `run_snobal` builds `forcing_pairs` as `(record[i], record[i+1])` pairs. The model consumes `N-1` timesteps for an `N`-row input DataFrame. The last row is only used as `input2` of the penultimate step.

2. **`output_rec` carries state**: The caller must preserve and pass the same `output_rec` dict across all timesteps. It initialises the snowpack and is mutated to reflect the updated state after each call.

3. **`mask` controls execution**: Pixels with `output_rec["mask"][n] == 0` are silently skipped by `call_snobal`. All non-masked pixels must have valid state values.

4. **OpenMP thread safety**: All `snobal.h` global variables are `#pragma omp threadprivate`. The library is safe for parallel pixel iteration but **not** safe for concurrent calls on the same pixel from different threads.

5. **`first_step` flag off-by-one**: In `pysnobal.py`, `first_step` is set via `int(i == 1)`, so it fires on the second iteration (index 1), not the first (index 0). New callers should match this behaviour or audit the intent.
