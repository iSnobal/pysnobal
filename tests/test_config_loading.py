from pathlib import Path

import pytest
from pysnobal.pysnobal import _load_override_config, load_config


@pytest.mark.parametrize(
    "config_flag",
    [
        ("--config"),
        ("-c"),
    ],
)
def test_config_load(monkeypatch, config_flag):
    # Get path to this test file’s folder
    tests_dir = Path(__file__).parent

    # Build path to the data file
    config_file = tests_dir / "data" / "config" / "baseline_config.yaml"

    # Load actual
    actual = load_config(config_file)

    monkeypatch.setattr("sys.argv", ["pysnobal", config_flag, str(config_file)])
    result = _load_override_config()

    assert result == actual


@pytest.mark.parametrize(
    "override_flag, override_args",
    [
        (
            "--override",
            [
                "init.snow_depth_cm=100",
                "init.bulk_snow_density_kgm-3=400",
                "init.active_layer_temp_degC=-1",
                "init.avg_snow_temp_degC=-1",
                "init.h2o_sat_%=5",
                "defaults.max_h2o_vol_frac=0.1",
                "defaults.max_active_layer_thickness_m=0.05",
            ],
        ),
        (
            "-o",
            [
                "init.snow_depth_cm=100",
                "init.bulk_snow_density_kgm-3=400",
                "init.active_layer_temp_degC=-1",
                "init.avg_snow_temp_degC=-1",
                "init.h2o_sat_%=5",
                "defaults.max_h2o_vol_frac=0.1",
                "defaults.max_active_layer_thickness_m=0.05",
            ],
        ),
    ],
)
def test_config_load_and_override(monkeypatch, override_flag, override_args):
    # Get path to this test file’s folder
    tests_dir = Path(__file__).parent

    # Build path to the data file
    config_file = tests_dir / "data" / "config" / "baseline_config.yaml"
    validation_file = tests_dir / "data" / "config" / "override_config.yaml"

    # Load actual
    actual = load_config(validation_file)

    monkeypatch.setattr(
        "sys.argv", ["pysnobal", "-c", str(config_file), override_flag] + override_args
    )
    result = _load_override_config()

    assert result == actual


@pytest.mark.parametrize(
    "override_arg",
    [
        ("defaults.max_h2o_vol_frac"),
        ("default.max_h2o_vol_frac=0.1"),
        ("defaults.max_h2o_vol=0.1"),
    ],
)
def test_config_load_and_override_exceptions(monkeypatch, override_arg):
    # Get path to this test file’s folder
    tests_dir = Path(__file__).parent

    # Build path to the data file
    config_file = tests_dir / "data" / "config" / "baseline_config.yaml"

    monkeypatch.setattr(
        "sys.argv", ["pysnobal", "-c", str(config_file), "-o", override_arg]
    )
    with pytest.raises(ValueError):
        _load_override_config()
