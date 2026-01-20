from pathlib import Path

import pandas as pd
import pytest
from pysnobal.pysnobal import load_config, run_pysnobal, run_snobal


def test_pysnobal_cli_entrypoint_real_data(monkeypatch, tmp_path):
    tests_dir = Path(__file__).parent

    config_file = tests_dir / "data" / "config" / "baseline_config.yaml"

    input_path = tests_dir / "data" / "input" / "pysnobal_test_input_rcew.csv"
    output_path = tmp_path / "pysnobal_test_output.csv"

    monkeypatch.setattr(
        "sys.argv",
        [
            "pysnobal",
            "-c",
            str(config_file),
            "-o",
            f"io.forcing_path={str(input_path)}",
            f"io.output_path={str(output_path)}",
        ],
    )

    run_pysnobal()

    result_df = pd.read_csv(output_path)

    expected_output_file = (
        tests_dir / "data" / "expected" / "pysnobal_test_output_rcew.csv"
    )
    expected_df = pd.read_csv(expected_output_file)

    # TODO: figure out why these don't match between runs
    drop_list = [
        "inter_layer_heat_flux_Wm-2",
        "delta_active_layer_energy_Wm-2",
    ]

    pd.testing.assert_frame_equal(
        result_df.drop(columns=drop_list),
        expected_df.drop(columns=drop_list),
        check_exact=False,
    )


def test_pysnobal_functional_entrypoint_real_data(tmp_path):
    tests_dir = Path(__file__).parent

    config_file = tests_dir / "data" / "config" / "baseline_config.yaml"
    config = load_config(config_file)

    input_path = tests_dir / "data" / "input" / "pysnobal_test_input_rcew.csv"
    forcing_df = pd.read_csv(input_path, index_col=0, parse_dates=True)

    result_df = run_snobal(forcing_df, config)

    expected_output_file = (
        tests_dir / "data" / "expected" / "pysnobal_test_output_rcew.csv"
    )
    expected_df = pd.read_csv(
        expected_output_file, index_col="Datetime", parse_dates=True
    )

    # TODO: figure out why these don't match between runs
    drop_list = [
        "inter_layer_heat_flux_Wm-2",
        "delta_active_layer_energy_Wm-2",
    ]

    pd.testing.assert_frame_equal(
        result_df.drop(columns=drop_list).reset_index(),
        expected_df.drop(columns=drop_list).reset_index(),
        check_exact=False,
    )
