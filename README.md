# Python Snobal (PySnobal)
PySnobal wraps the Snobal (1D point model) and iSnobal (2D spatially distributed model) snow mass and energy balance models with Python, providing a convenient interface for running the models and integratting them into larger frameworks, like the [Automated Water Supply Model (AWSM)](https://github.com/iSnobal/awsm).

# Installation

Model setup uses the `conda` (or `mamba`) environment management software.
The recommended approach involves installing the complete iSnobal modelling environment, which includes pysnobal and related tools, as described in [iSnobal instructions](https://github.com/iSnobal/model_setup).

# Usage
## PySnobal (point model)
Using PySnobal to invoke the Snobal point model involves three main steps:

### 1. Prepare forcing data
Prepare a .csv with the required forcing variables, correct units, and expected column names:

| **Variable**                  | **Unit**             | **Expected Column Name**  |
|-------------------------------|----------------------|---------------------------|
| Datetime                      | e.g., YYYYMMDD HH:MM | -                         |
| Net Shortwave Radiation       | $W/m^2$              | net_solar_Wm-2            |
| Downwelling Thermal Radiation | $W/m^2$              | downwelling_thermal_Wm-2  |
| Air Temperature               | $degC$               | temp_air_degC             |
| Soil Temperature              | $degC$               | temp_ground_degC          |
| Vapor Pressure                | $Pa$                 | vapor_pressure_Pa         |
| Wind Speed                    | $m/s$                | wind_speed_ms-1           |
| Precipitation Mass            | $mm$                 | precip_mass_mm            |
| Precipitation Temperature     | $degC$               | precip_temp_degC          |
| Precipitation Snow Fraction   | 0-1                  | snow_precip_fraction      |
| Precipitating Snow Density    | $kg/m^3$             | snow_precip_density_kgm-3 |

**Note**: A boilerplate Jupyter Notebook `/pysnobal/notebooks/pysnobal_data_prep.ipynb` has been provided to help facilitate this process.

### 2. Confiugre model

Create a configuration file, edit the required inputs, and optionally define the initial snowpack state or override default values. A configuration file with the epxected structure is provided in `/pysnobal/config/config.yaml`.

### 3. Invoke model

PySnobal can be invoked from the command line or Python code.

#### Command-Line Interface 
````Bash
usage: pysnobal [-h] --config CONFIG [--override [OVERRIDE ...]]

Run Snobal using the forcing data and model parameters in config. Optionally
provide overrides to config as args.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to YAML config file.
  -o [OVERRIDE ...], --override [OVERRIDE ...]
                        Override config values, e.g. -o
                        io.forcing_path=./cssl_wy17_forcing.csv
                        params.elevation_m=2101
````

##### Example 
````Bash
pysnobal -c config/config.yaml -o io.forcing_path=test_data.csv params.roughness_length_m=0.005
````

#### API Call
````python
import pandas as pd
import pysnobal.pysnobal as pysnobal

config = pysnobal.load_config('<path_to_yaml>')
forcing_df = pd.read_csv('<path_to_csv>', parse_dates=True, index_col=0)
output_df = pysnobal.run_snobal(forcing_data_df, config, show_pbar=False)
````
**Note**: A similar example is provided in `/pysnobal/notebooks/pysnobal_notebook_workflow.ipynb`.

## iPySnobal (spatially distributed model)

The recommended approach for running iSnobal is to use [AWSM](https://github.com/iSnobal/awsm), which greatly simiplifies preparing the inputs and running the model.

## Changing defaults, naming conventions, etc.
Snobal model defaults (e.g., dynamic timestep thresholds) and PySnobal configuration details (e.g., mappings between forcing variable names in the user facing data structure and the forcing variable names expected by Snobal) are defined in `/pysnobal/pysnobal/defaults.py`. Such details can be customized by modifying `defaults.py` directly, but care must be taken to ensure names and conventions expected internally by Snobal are not broken.

# History
## Fork of pysnobal

This is a fork of the [USDA-ARS-NWRC pysnobal](https://github.com/USDA-ARS-NWRC/pysnobal) repo to support continued maintainence and improvement of pysnobal.

## Snobal Lineage and Naming
- Snobal: **sno**w mass and energy **bal**ance model (1D point model; written in C)
- iSnobal: **sno**w mass and energy **bal**ance model distributed over an **i**mage (2D model in which Snobal is run at each grid cell; written in C)
- PySnobal: Refers to (1) the **Py**thon module used to invoke **Snobal** and (2) the greater Python wrapper for both Snobal and iSnobal
- iPySnobal: **Py**thon module used to invoke **iSnobal**
- Automated Water Supply Model (AWSM): a framework that simplifies configuring and running iPySnobal

iSnobal, iPySnobal, and AWSM are sometimes used interchangeably to refer to modeling the snowpack over a grid using, at the lowest level, iSnobal binaries. 

Snobal and PySnobal are often used interchangeably to refer to modeling the snowpack at a point using, at the lowest level, Snobal binaries.

## Selected Publications
* Marks, D., Domingo, J., Susong, D., Link, T., & Garen, D. (1999). A spatially distributed energy balance snowmelt model for application in mountain basins. Hydrological Processes, 13(12–13), 1935–1959. https://doi.org/10.1002/(SICI)1099-1085(199909)13:12/13%253C1935::AID-HYP868%253E3.0.CO;2-C

* Marks, D., & Dozier, J. (1992). Climate and energy exchange at the snow surface in the Alpine Region of the Sierra Nevada: 2. Snow cover energy balance. Water Resources Research, 28(11), 3043–3054. https://doi.org/10.1029/92WR01483

* Meyer, J., Horel, J., Kormos, P., Hedrick, A., Trujillo, E., & Skiles, S. M. (2023). Operational water forecast ability of the HRRR-iSnobal combination: An evaluation to adapt into production environments. Geoscientific Model Development, 16(1), 233–250. https://doi.org/10.5194/gmd-16-233-2023