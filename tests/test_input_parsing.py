from pathlib import Path

import numpy as np
import pandas as pd
import pysnobal.defaults as defaults
import pytest
from pysnobal.pysnobal import (
    _check_config,
    _check_forcing_df,
    _parse_inputs,
    load_config,
)


def get_well_formed_forcing_df():
    # Create a 24-hour hourly index
    index = pd.date_range("2026-01-19 00:00", periods=24, freq="H")

    # Generate random data for each column
    # Here, using normal or uniform random distributions as placeholders
    data = {
        col: np.random.rand(len(index))  # random values between 0 and 1
        for col in defaults.FORCING_NAMES_CUSTOM2SNOBAL.keys()
    }

    # Create the DataFrame
    df = pd.DataFrame(data, index=index)

    return df


def test_check_forcing_df():
    assert _check_forcing_df(get_well_formed_forcing_df()) == 3600


@pytest.mark.parametrize(
    "df",
    [
        get_well_formed_forcing_df().drop(columns=[v])
        for v in defaults.FORCING_NAMES_CUSTOM2SNOBAL.keys()
    ],
)
def test_check_forcing_df_missing_col(df):
    with pytest.raises(ValueError):
        _check_forcing_df(df)


def test_check_forcing_df_nonuniform_timestep():
    df = get_well_formed_forcing_df()
    df.drop(index=pd.Timestamp("2026-01-19 05:00"), inplace=True)

    with pytest.raises(ValueError):
        _check_forcing_df(df)


@pytest.mark.parametrize("col", defaults.FORCING_NAMES_CUSTOM2SNOBAL.keys())
def test_check_forcing_df_not_serially_complete(col):
    df = get_well_formed_forcing_df()
    df.loc[pd.Timestamp("2026-01-19 05:00"), col] = np.nan
    with pytest.raises(ValueError):
        _check_forcing_df(df)


@pytest.mark.parametrize("case", ["baseline", "override"])
def test_check_config(case):
    # Get path to this test file’s folder
    tests_dir = Path(__file__).parent

    # Build path to the data file
    config_file = tests_dir / "data" / "config" / f"{case}_config.yaml"
    config = load_config(config_file)

    expected_file = tests_dir / "data" / "config" / f"{case}_expected.yaml"
    expected = load_config(expected_file)

    _check_config(config)

    assert config == expected


@pytest.mark.parametrize(
    "group, param, bad_val",
    [(group, None, None) for group in ["io", "z", "params"]]
    + [("io", "output_path", None)]
    + [("z", v, None) for v in ["air_temp_m", "soil_temp_m", "wind_speed_m"]]
    + [("z", v, -1) for v in ["air_temp_m", "soil_temp_m", "wind_speed_m"]]
    + [("params", param, None) for param in ["elevation_m", "roughness_length_m"]]
    + [
        ("init", i, None)
        for i in [
            "snow_depth_cm",
            "bulk_snow_density_kgm-3",
            "active_layer_temp_degC",
            "avg_snow_temp_degC",
            "h2o_sat_%",
        ]
    ],
)
def test_check_config_exceptions(group, param, bad_val):
    # Get path to this test file’s folder
    tests_dir = Path(__file__).parent

    # Build path to the data file
    config_file = tests_dir / "data" / "config" / "baseline_config.yaml"
    config = load_config(config_file)

    if param is None:
        del config[group]
    elif group == "init":
        del config[group][param]
    else:
        config[group][param] = bad_val

    with pytest.raises(ValueError):
        _check_config(config)


@pytest.mark.parametrize("case", ["baseline", "override"])
def test_parse_inputs(case):
    df = get_well_formed_forcing_df()

    # Get path to this test file’s folder
    tests_dir = Path(__file__).parent

    # Build path to the data file
    config_file = tests_dir / "data" / "config" / f"{case}_config.yaml"
    config = load_config(config_file)

    expected_file = tests_dir / "data" / "config" / f"{case}_expected.yaml"
    expected = load_config(expected_file)

    forcing_data_df, mh, params, timestep_info, output_rec = _parse_inputs(df, config)

    assert sorted(forcing_data_df.columns) == sorted(
        defaults.FORCING_NAMES_CUSTOM2SNOBAL.values()
    )

    assert mh == {
        "z_t": expected["z"]["air_temp_m"],
        "z_g": expected["z"]["soil_temp_m"],
        "z_u": expected["z"]["wind_speed_m"],
    }

    assert params == {
        "relative_heights": expected["defaults"]["relative_heights"],
        "max_h2o_vol": expected["defaults"]["max_h2o_vol_frac"],
        "max_z_s_0": expected["defaults"]["max_active_layer_thickness_m"],
    }

    for i, level in enumerate(timestep_info):
        assert sorted(list(level.keys())) == [
            "intervals",
            "level",
            "output",
            "threshold",
            "time_step",
        ]

        if i == 0:
            assert level["level"] is not None
            assert level["output"] is not None
            assert level["time_step"] is not None
        else:
            assert np.all(value is None for value in level.values())

        assert level["level"] == i

        if i < len(timestep_info) - 2:
            assert timestep_info[i]["time_step"] >= timestep_info[i]["time_step"]
            if i > 0:
                assert timestep_info[i]["threshold"] >= timestep_info[i]["threshold"]

    for v in output_rec.values():
        assert v.ndim >= 2

    assert output_rec["elevation"].ravel()[0] == expected["params"]["elevation_m"]
    assert output_rec["z_0"].ravel()[0] == expected["params"]["roughness_length_m"]
    assert np.all(output_rec["mask"].ravel()) == 1

    for key in defaults.OUTPUT_NAMES_SNOBAL2CUSTOM.keys():
        if defaults.OUTPUT_NAMES_SNOBAL2CUSTOM[key] in expected["init"].keys():
            assert output_rec[key] == np.atleast_2d(
                expected["init"][defaults.OUTPUT_NAMES_SNOBAL2CUSTOM[key]]
            )
        else:
            assert output_rec[key] == np.atleast_2d(0.0)
