import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import progressbar
import yaml

import pysnobal.defaults as defaults
import pysnobal.utils as utils
from pysnobal.c_snobal import snobal


def load_config(path: Path) -> dict[str, Any]:
    """
    Loads Pysnobal YAML config file into a Python dictionary.

    Args:
        path (Path): Path to configuration file.

    Returns:
        dict: Model configuration parameters.
    """
    # TODO: check if file exists
    with open(path, "r") as f:
        return yaml.safe_load(f)


def run_snobal(
    forcing_data_df: pd.DataFrame, config: dict[str, Any], show_pbar: bool = False
) -> pd.DataFrame:
    """
    Run Snobal using the provided forcing data and model configuration parameters.

    TODO: explain name mapping, error checking of inputs, etc.

    Args:
        forcing_data_df (pd.DataFrame): Forcing data.
        config (dict): Model configuration parameters.
        show_pbar (bool): Prints a progressbar to stdout when True.

    Returns:
        pd.DataFrame: Model output terms.
    """
    # translate forcing_data to data structures expected by do_tstep_grid
    forcing_data_df, mh, params, timestep_info, output_rec = _parse_inputs(
        forcing_data_df, config
    )

    # set time components of output_rec
    # TODO if want to support starting from middle of run: need to define output_rec['current_time'] and output_rec['time_since_out']

    # pre-make forcing pairs (vectorized opperation, faster than iterating, memory shouldn't be an issue)
    forcing_records = forcing_data_df.to_dict(orient="records")
    datetime = forcing_data_df.index.to_list()
    forcing_pairs = {
        datetime[i]: (
            {k: np.atleast_2d(v) for k, v in forcing_records[i].items()},
            {k: np.atleast_2d(v) for k, v in forcing_records[i + 1].items()},
        )
        for i in range(len(forcing_records) - 1)
    }

    # run model loop, invoking the Snobal binding, keeping running list of output
    dt_dic = {
        "Datetime": []
    }  # TODO: can use dictionary intersection operator to make more elegant in more recent versions of python
    eb_dic = {defaults.OUTPUT_NAMES_SNOBAL2CUSTOM[col]: [] for col in defaults.EM_OUT}
    snow_dic = {
        defaults.OUTPUT_NAMES_SNOBAL2CUSTOM[col]: [] for col in defaults.SNOW_OUT
    }
    running_output = {**dt_dic, **eb_dic, **snow_dic}

    if show_pbar:
        pbar = progressbar.ProgressBar(max_value=len(forcing_pairs))

    for i, (dt, forcing_pair) in enumerate(forcing_pairs.items()):
        # call model
        input1 = forcing_pair[0]
        input2 = forcing_pair[1]
        is_first = int(i == 1)
        rt = snobal.do_tstep_grid(
            input1, input2, output_rec, timestep_info, mh, params, first_step=is_first
        )

        # check return value and raise exception as needed
        if rt != -1:
            raise ValueError(f"pointsnobal error on time step {dt}")

        # output data at the frequency and last time step
        _append_output(running_output, dt, output_rec)

        if show_pbar:
            pbar.update(i)

    output_df = pd.DataFrame(running_output)
    output_df.index = output_df["Datetime"]
    return output_df


def _override_config(config: dict[str, Any], overrides: list[str]) -> dict[str, Any]:
    """
    Update nested config dict using a list of key=value strings.

    Supports dot notation for nested keys, e.g. 'params.elevation_m=1234'.

    Args:
        config (dict): Model configuration parameters.
        overrides (list[str]): Paramaeters to overide.

    Returns:
        dict: Updated model configuration parameters.
    """
    for override in overrides:
        if "=" not in override:
            raise ValueError(f"Invalid override '{override}'. Expected key=value.")
        key, value = override.split("=", 1)

        # Convert types if possible
        try:
            value = eval(value)
        except Exception:
            pass

        # Navigate nested keys
        keys = key.split(".")
        subconfig = config
        for k in keys[:-1]:
            subconfig = subconfig.get(k)
            print(subconfig)
            if subconfig is None:
                raise ValueError(
                    f"Invalid override '{key}'. Parameter not accepted in config."
                )

        if subconfig.get(keys[-1]) is None:
            raise ValueError(
                f"Invalid override '{key}'. Parameter not accepted in config."
            )

        subconfig[keys[-1]] = value

    return config


def _load_override_config() -> dict[str, Any]:
    """
    Parse command-line arguments and load model configuration with optional overrides.

    The --config/-c command line argument is required when invoking the model from the command line.
    Optional override arguments of the form --override/-o <param_header>.<param_name>=<value> can
    be used to override the default value in the config file.

    Returns:
        dict: Model configuration parameters.
    """
    # create parser with options for config path and override
    parser = argparse.ArgumentParser(
        description="Run Snobal using the forcing data and model parameters in config. Optionally provide overrides to config as args."
    )
    parser.add_argument(
        "--config", "-c", type=str, required=True, help="Path to YAML config file."
    )
    parser.add_argument(
        "--override",
        "-o",
        nargs="*",
        default=[],
        help="Override config values, e.g. -o io.forcing_path=./cssl_wy17_forcing.csv params.elevation=2101",
    )

    args = parser.parse_args()
    config = load_config(args.config)

    # update config with overwritten params
    config = _override_config(config, args.override)

    return config


def _check_forcing_df(forcing_data_df: pd.DataFrame) -> float:
    """
    Verify forcing data contains required terms, is complete, uniform, and properly named.

    Args:
        forcing_data_df (pd.DataFrame): Forcing data.

    Returns:
        float: Data timestep in seconds.
    """
    # verify all forcing terms are present
    for k in defaults.FORCING_NAMES_CUSTOM2SNOBAL.keys():
        if k not in forcing_data_df.columns:
            raise ValueError(
                f"Dataframe missing {k}. Dataframe must contain the following columns: {list(defaults.FORCING_NAMES_CUSTOM2SNOBAL.keys())}"
            )

    # calculate timestep frequency in seconds
    timesteps = (
        np.unique(np.diff(forcing_data_df.index)).astype("timedelta64[s]").astype(float)
    )  # TODO can make more readable using .diff() if using more recent version of python
    if len(timesteps) > 1:
        raise ValueError(
            f"Dataframe has a non-uniform timestep. Found the following timesteps: {timesteps}"
        )

    data_tstep_sec = timesteps[0]

    # verify the inputs are serially complete (no NaNs)
    for col, nan in (
        forcing_data_df[defaults.FORCING_NAMES_CUSTOM2SNOBAL.keys()]
        .isna()
        .sum()
        .items()
    ):
        if nan > 0:
            raise ValueError(
                f"Column {col} is not serially complete (i.e. contains NaN)"
            )

    # TODO: incorporate line 304 from the original pysnobal?

    return data_tstep_sec


def _check_config(config: dict[str, Any], data_tstep_sec: float) -> None:
    """
    Verify config has required components and correct format; backfill with defaults as needed.

    Args:
        config (dict): Model configuration parameters.
        data_tstep_sec (float): Data timestep in seconds.

    Returns
        None
    """
    # check config for required sections
    for group in ["io", "z", "params"]:
        if config.get(group) is None:
            raise ValueError(f"config must contain a nested dictionary for {group}")

    # check to make sure output path provided
    if config["io"].get("output_path") is None:
        raise ValueError(
            "config must contain a path for the output data: {'io' : {'output_path' : <your path>}}"
        )

    # check to make sure input heights provided and non-negative
    for h in ["air_temp_m", "soil_temp_m", "wind_speed_m"]:
        if config["z"].get(h) is None:
            raise ValueError(
                f"config must contain the instrument height/depth for {h}: {{'z' : {{{h} : <instrument height meters>}}}}"
            )

        if config["z"][h] < 0:
            raise ValueError(f"instrument height/depth for {h} must be positive")

    # check to make sure input parameters are provided
    for p in ["elevation_m", "roughness_length_m"]:
        if config["params"].get(p) is None:
            raise ValueError(
                f"config must contain specify the value for {p}: {{'params' : {{{p} : <value>}}}}"
            )

    # backfill model parameters with defaults
    if (config.get("init") is None) or all(
        value is None for value in config["init"].values()
    ):
        config["init"] = defaults.DEFAULT_SNOWPACK
    else:
        for s in []:
            if config["init"].get(s) is None:
                raise ValueError(
                    f"if specifying the initial snowpack state in config, config must contain {s}: {{'init' : {{{s} : <value>}}}}"
                )

    if config.get("defaults") is None:
        config["defaults"] = defaults.DEFAULT_PARAMS
    else:
        for k in defaults.DEFAULT_PARAMS:
            if config["defaults"].get(k) is None:
                config["defaults"][k] = defaults.DEFAULT_PARAMS[k]

    # TODO: check to make sure tstep lengths divide evenly


def _parse_inputs(
    forcing_data_df: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, dict, dict, list[dict], dict]:
    """
    Check forcing data and config correctness before converting to Snobal datastructures.

    Verifies all required forcing variables and forcing parameters exists and are formatted
    correctly. Translates temperature to Kelvin, as expected by Snobal. Translates externally
    defined variable names to variables names used internally within Snobal. Prepares the data
    structures (mh, params, timestep_info, output_rec) expected by Snobal and the Cython
    intermediary.

    Args:
        forcing_data_df (pd.DataFrame): Forcing data.
        config (dict): Model configuration parameters.

    Returns:
        pd.DataFrame: Reformatted forcing data.
        dict: Measurement height dictionary.
        dict: Parameter dictionary.
        list[dict]: timestep_info data structure.
        dict: output_rec data structure.
    """
    # check validity of inputs
    data_tstep_sec = _check_forcing_df(forcing_data_df)
    _check_config(config, data_tstep_sec)

    # rename forcing dataframe and convert degC to K
    forcing_data_df.rename(columns=defaults.FORCING_NAMES_CUSTOM2SNOBAL, inplace=True)
    forcing_data_df["T_a"] += utils.C_TO_K
    forcing_data_df["T_g"] += utils.C_TO_K
    forcing_data_df["T_pp"] += utils.C_TO_K

    # assemble measurement height dictionary
    mh = {
        "z_t": config["z"]["air_temp_m"],
        "z_g": config["z"]["soil_temp_m"],
        "z_u": config["z"]["wind_speed_m"],
    }

    # assemble parameter dictionary
    params = {
        "relative_heights": config["defaults"]["relative_heights"],
        "max_h2o_vol": config["defaults"]["max_h2o_vol_frac"],
        "max_z_s_0": config["defaults"]["max_active_layer_thickness_m"],
    }

    # prepare t_step info dat structure
    # TODO: make output interval a user-configured parameter, but cannot be smaller than data_tstep
    timestep_info = [
        {
            "level": defaults.DATA_TIMESTEP,
            "output": defaults.DIVIDED_TIMESTEP,
            "threshold": None,
            "time_step": data_tstep_sec,
            "intervals": None,
        },
        {
            "level": defaults.NORMAL_TIMESTEP,
            "output": False,
            "threshold": config["defaults"]["normal_tstep_mass_thresh_kgm-2"],
            "time_step": utils.min2sec(config["defaults"]["normal_tstep_min"]),
        },
        {
            "level": defaults.MEDIUM_TIMESTEP,
            "output": False,
            "threshold": config["defaults"]["medium_tstep_mass_thresh_kgm-2"],
            "time_step": utils.min2sec(config["defaults"]["medium_tstep_min"]),
        },
        {
            "level": defaults.SMALL_TIMESTEP,
            "output": False,
            "threshold": config["defaults"]["small_tstep_mass_thresh_kgm-2"],
            "time_step": utils.min2sec(config["defaults"]["small_tstep_min"]),
        },
    ]

    for i in range(1, 4):
        timestep_info[i]["intervals"] = int(
            timestep_info[i - 1]["time_step"] / timestep_info[i]["time_step"]
        )

    # prepare output_rec datastructure
    elevation = np.atleast_2d(config["params"]["elevation_m"])
    mask = np.atleast_2d(1)
    roughness_length = np.atleast_2d(config["params"]["roughness_length_m"])

    output_rec = {"elevation": elevation, "mask": mask, "z_0": roughness_length}

    # add snobal state variables and EB terms
    for key in defaults.OUTPUT_NAMES_SNOBAL2CUSTOM.keys():
        output_rec[key] = np.atleast_2d(0.0)

    # initialize snow conditions
    for s in config["init"]:
        output_rec[defaults.PARAM_NAMES_CUSTOM2SNOBAL[s]] = np.atleast_2d(
            config["init"][s]
        )

    return forcing_data_df, mh, params, timestep_info, output_rec


def _append_output(
    running_output: dict[str, list], dt: pd.Timestamp, output_rec: dict[str, Any]
) -> None:
    """
    Append timestep output to running list of output.

    Args:
        running_output (dict): Running output (mapping variable name to list of values).
        dt (pd.Timestamp): Timestamp for start of current timestep.
        output_rec (dict): Output returned by Snobal for the current timestep.

    Returns
        None
    """
    # add datetime for timestep
    running_output["Datetime"].append(dt)

    # add EB terms
    for x in defaults.EM_OUT:
        running_output[defaults.OUTPUT_NAMES_SNOBAL2CUSTOM[x]].append(
            output_rec[x][0][0]
        )

    # add snow terms
    for x in defaults.SNOW_OUT:
        v_name = defaults.OUTPUT_NAMES_SNOBAL2CUSTOM[x]
        if "temp" in v_name:
            running_output[v_name].append(output_rec[x][0][0] - utils.C_TO_K)
        else:
            running_output[v_name].append(output_rec[x][0][0])


def main():
    """
    Excute model using config and optional overrides from the command line.
    """
    config = _load_override_config()

    # open forcing data
    forcing_data_df = pd.read_csv(
        config["io"]["forcing_path"], parse_dates=True, index_col=0
    )

    # run model
    output_df = run_snobal(forcing_data_df, config, show_pbar=True)

    # save output to file
    output_df.to_csv(config["io"]["output_path"])


if __name__ == "__main__":
    main()
