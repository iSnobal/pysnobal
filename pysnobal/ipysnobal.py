import numpy as np

DATA_TIMESTEP = 0
NORMAL_TIMESTEP = 1
MEDIUM_TIMESTEP = 2
SMALL_TIMESTEP = 3

DEFAULT_NORMAL_THRESHOLD = 60.0
DEFAULT_MEDIUM_THRESHOLD = 10.0
DEFAULT_SMALL_THRESHOLD = 1.0

DEFAULT_MEDIUM_TIMESTEP = 15.0
DEFAULT_SMALL_TIMESTEP = 1.0

WHOLE_TIMESTEP = 1  # output when timestep is not divided
DIVIDED_TIMESTEP = 2  # output when timestep is divided


def min2sec(x):
    return x * 60


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
    timestep_info[DATA_TIMESTEP]["time_step"] = min2sec(data_timestep_min)

    timestep_info[NORMAL_TIMESTEP]["time_step"] = min2sec(DEFAULT_NORMAL_THRESHOLD)
    timestep_info[NORMAL_TIMESTEP]["intervals"] = int(
        data_timestep_min / DEFAULT_NORMAL_THRESHOLD
    )

    timestep_info[MEDIUM_TIMESTEP]["time_step"] = min2sec(DEFAULT_MEDIUM_TIMESTEP)
    timestep_info[MEDIUM_TIMESTEP]["intervals"] = int(
        DEFAULT_NORMAL_THRESHOLD / DEFAULT_MEDIUM_TIMESTEP
    )

    timestep_info[SMALL_TIMESTEP]["time_step"] = min2sec(DEFAULT_SMALL_TIMESTEP)
    timestep_info[SMALL_TIMESTEP]["intervals"] = int(
        DEFAULT_MEDIUM_TIMESTEP / DEFAULT_SMALL_TIMESTEP
    )

    # output
    if config["output"]["output_mode"] == "data":
        timestep_info[DATA_TIMESTEP]["output"] = DIVIDED_TIMESTEP
    elif config["output"]["output_mode"] == "normal":
        timestep_info[NORMAL_TIMESTEP]["output"] = WHOLE_TIMESTEP | DIVIDED_TIMESTEP
    elif config["output"]["output_mode"] == "all":
        timestep_info[NORMAL_TIMESTEP]["output"] = WHOLE_TIMESTEP
        timestep_info[MEDIUM_TIMESTEP]["output"] = WHOLE_TIMESTEP
        timestep_info[SMALL_TIMESTEP]["output"] = WHOLE_TIMESTEP
    else:
        timestep_info[DATA_TIMESTEP]["output"] = DIVIDED_TIMESTEP

    # mass thresholds for run timesteps
    timestep_info[NORMAL_TIMESTEP]["threshold"] = DEFAULT_NORMAL_THRESHOLD
    timestep_info[MEDIUM_TIMESTEP]["threshold"] = DEFAULT_MEDIUM_THRESHOLD
    timestep_info[SMALL_TIMESTEP]["threshold"] = DEFAULT_SMALL_THRESHOLD

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


def initialize(init):
    # create the OUTPUT_REC with additional fields and fill
    # There are a lot of additional terms that the original output_rec does not
    # have due to the output function being outside the C code which doesn't
    # have access to those variables
    sz = init["elevation"].shape

    fields = [
        "E_s_sum",
        "G_0_bar",
        "G_bar",
        "H_bar",
        "L_v_E_bar",
        "M_bar",
        "R_n_bar",
        "T_s",
        "T_s_0",
        "T_s_l",
        "cc_s",
        "cc_s_0",
        "cc_s_l",
        "current_time",
        "delta_Q_0_bar",
        "delta_Q_bar",
        "elevation",
        "h2o",
        "h2o_max",
        "h2o_sat",
        "h2o_total",
        "h2o_vol",
        "layer_count",
        "m_s",
        "m_s_0",
        "m_s_l",
        "mask",
        "melt_sum",
        "rho",
        "ro_pred_sum",
        "time_since_out",
        "z_0",
        "z_s",
        "z_s_0",
        "z_s_l",
    ]
    # Initialize according to the topo shape
    s = {key: np.zeros(sz) for key in fields}

    # Update values from config
    for key, val in init.items():
        if key in fields:
            s[key] = val

    return s
