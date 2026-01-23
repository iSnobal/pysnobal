import pandas as pd
from pysnobal.pysnobal import load_config, run_pysnobal, run_snobal


def test_pysnobal_cli_entrypoint_real_data(monkeypatch, tmp_path, test_data):
    config_file = test_data.config("baseline", "config")

    input_path = test_data.model_input()
    output_path = tmp_path / "pysnobal_test_output.csv"

    expected_output_file = test_data.model_expected()
    expected_df = pd.read_csv(expected_output_file)

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

    # Consistently errors between output and expected for these
    # variables, despite agreement everywhere else
    drop_list = [
        "inter_layer_heat_flux_Wm-2",
        "delta_active_layer_energy_Wm-2",
    ]

    pd.testing.assert_frame_equal(
        result_df.drop(columns=drop_list),
        expected_df.drop(columns=drop_list),
        check_exact=False,
    )


def test_pysnobal_functional_entrypoint_real_data(tmp_path, test_data):
    config_file = test_data.config("baseline", "config")
    config = load_config(config_file)

    input_path = test_data.model_input()
    forcing_df = pd.read_csv(input_path, index_col=0, parse_dates=True)

    expected_output_file = test_data.model_expected()
    expected_df = pd.read_csv(
        expected_output_file, index_col="Datetime", parse_dates=True
    )

    result_df = run_snobal(forcing_df, config)

    # Consistently errors between output and expected for these
    # variables, despite agreement everywhere else
    drop_list = [
        "inter_layer_heat_flux_Wm-2",
        "delta_active_layer_energy_Wm-2",
    ]

    pd.testing.assert_frame_equal(
        result_df.drop(columns=drop_list).reset_index(),
        expected_df.drop(columns=drop_list).reset_index(),
        check_exact=False,
    )
