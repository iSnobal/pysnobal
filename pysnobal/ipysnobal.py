import numpy as np

from pysnobal import defaults, utils


def get_timestep_info(options, config):
    """
    Parse the options dict, set the default values if not specified
    """

    # initialize the time step info
    # 0 : data timestep
    # 1 : normal run timestep
    # 2 : medium  "     "
    # 3 : small   "     "

    timestep_info = []
    for i in range(4):
        t = {
            "level": i,
            "output": False,
            "threshold": None,
            "time_step": None,
            "intervals": None,
        }
        timestep_info.append(t)

    # The input data's time step must be between 1 minute and 6 hours.
    # If it is greater than 1 hour, it must be a multiple of 1 hour, e.g.
    # 2 hours, 3 hours, etc.

    data_timestep_min = float(options["time_step"])
    timestep_info[defaults.DATA_TIMESTEP]["time_step"] = utils.min2sec(
        data_timestep_min
    )

    timestep_info[defaults.NORMAL_TIMESTEP]["time_step"] = utils.min2sec(
        defaults.DEFAULT_PARAMS["normal_tstep_min"]
    )
    timestep_info[defaults.NORMAL_TIMESTEP]["intervals"] = int(
        data_timestep_min / defaults.DEFAULT_PARAMS["normal_tstep_min"]
    )

    timestep_info[defaults.MEDIUM_TIMESTEP]["time_step"] = utils.min2sec(
        defaults.DEFAULT_PARAMS["medium_tstep_min"]
    )
    timestep_info[defaults.MEDIUM_TIMESTEP]["intervals"] = int(
        defaults.DEFAULT_PARAMS["normal_tstep_min"]
        / defaults.DEFAULT_PARAMS["medium_tstep_min"]
    )

    timestep_info[defaults.SMALL_TIMESTEP]["time_step"] = utils.min2sec(
        defaults.DEFAULT_PARAMS["small_tstep_min"]
    )
    timestep_info[defaults.SMALL_TIMESTEP]["intervals"] = int(
        defaults.DEFAULT_PARAMS["medium_tstep_min"]
        / defaults.DEFAULT_PARAMS["small_tstep_min"]
    )

    # output
    if config["output"]["output_mode"] == "data":
        timestep_info[defaults.DATA_TIMESTEP]["output"] = defaults.DIVIDED_TIMESTEP
    elif config["output"]["output_mode"] == "normal":
        timestep_info[defaults.NORMAL_TIMESTEP]["output"] = (
            defaults.WHOLE_TIMESTEP | defaults.DIVIDED_TIMESTEP
        )
    elif config["output"]["output_mode"] == "all":
        timestep_info[defaults.NORMAL_TIMESTEP]["output"] = defaults.WHOLE_TIMESTEP
        timestep_info[defaults.MEDIUM_TIMESTEP]["output"] = defaults.WHOLE_TIMESTEP
        timestep_info[defaults.SMALL_TIMESTEP]["output"] = defaults.WHOLE_TIMESTEP
    else:
        timestep_info[defaults.DATA_TIMESTEP]["output"] = defaults.DIVIDED_TIMESTEP

    # mass thresholds for run timesteps
    timestep_info[defaults.NORMAL_TIMESTEP]["threshold"] = defaults.DEFAULT_PARAMS[
        "normal_tstep_mass_thresh_kgm-2"
    ]
    timestep_info[defaults.MEDIUM_TIMESTEP]["threshold"] = defaults.DEFAULT_PARAMS[
        "medium_tstep_mass_thresh_kgm-2"
    ]
    timestep_info[defaults.SMALL_TIMESTEP]["threshold"] = defaults.DEFAULT_PARAMS[
        "small_tstep_mass_thresh_kgm-2"
    ]

    # get the rest of the parameters
    params = {
        "data_timestep": data_timestep_min,
        "max_h2o_vol": options["max-h2o"],
        "max_z_s_0": options["max_z_s_0"],
        "out_filename": config["output"]["out_filename"],
        "stop_no_snow": options["c"],
        "temps_in_C": options["K"],
        "relative_heights": options["relative_heights"],
    }
    if params["out_filename"] is not None:
        params["out_file"] = open(params["out_filename"], "w")

    #     params['elevation'] = options['z']
    #     params['sn_filename'] = options['s']
    #     params['mh_filename'] = options['h']
    #     params['in_filename'] = options['i']
    #     params['pr_filename'] = options['p']

    return params, timestep_info


def initialize(init: dict) -> dict:
    """
    Create the expected key/values per for an OUTPUT_REC.

    This initializes to the struct defined in c_snobal/h/pysnobal.h that the C code
    writes to.

    Args:
        init: Dict with initial snowpack state and configuration values

    Returns:
        Dict with all required key/values per OUTPUT_REC
    """
    sz = init["elevation"].shape

    fields = (
        defaults.SNOW_OUT
        + defaults.EM_OUT
        + [
            "current_time",
            "elevation",
            "h2o_max",
            "h2o_total",
            "h2o_vol",
            "layer_count",
            "mask",
            "time_since_out",
            "z_0",
        ]
    )

    # Initialize with values from the init dict or with zeros if missing.
    # Also enforce float64 C-contiguous layout for all arrays as required by do_tstep_grid.
    s = {}
    for field in fields:
        s[field] = np.ascontiguousarray(init.get(field, np.zeros(sz)), dtype=np.float64)

    return s
