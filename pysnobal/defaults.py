# ***** Default Initial Conditions and Model Parameters *****

DEFAULT_SNOWPACK = {
    "snow_depth_cm": 0,
    "bulk_snow_density_kgm-3": 0,
    "active_layer_temp_degC": 0,
    "avg_snow_temp_degC": 0,
    "h2o_sat_%": 0,
}

DEFAULT_PARAMS = {
    "relative_heights": False,
    "max_h2o_vol_frac": 0.01,
    "max_active_layer_thickness_m": 0.25,
    "normal_tstep_mass_thresh_kgm-2": 60,
    "medium_tstep_mass_thresh_kgm-2": 10,
    "small_tstep_mass_thresh_kgm-2": 1,
    "normal_tstep_min": 60,
    "medium_tstep_min": 15,
    "small_tstep_min": 1,
}

# ***** Output Variables *****

EM_OUT = [
    "R_n_bar",
    "H_bar",
    "L_v_E_bar",
    "M_bar",
    "G_bar",
    "G_0_bar",
    "delta_Q_bar",
    "delta_Q_0_bar",
]
SNOW_OUT = [
    "rho",
    "T_s",
    "T_s_0",
    "T_s_l",
    "z_s",
    "z_s_0",
    "z_s_l",
    "cc_s",
    "cc_s_0",
    "cc_s_l",
    "m_s",
    "m_s_0",
    "m_s_l",
    "h2o",
    "h2o_sat",
    "E_s_sum",
    "melt_sum",
    "ro_pred_sum",
]

# ***** Mappings from Custom Variable Names to Names Snobal Expects *****

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

PARAM_NAMES_CUSTOM2SNOBAL = {
    "snow_depth_cm": "snow_depth",
    "bulk_snow_density_kgm-3": "bulk_snow_density",
    "active_layer_temp_degC": "active_layer_temp",
    "avg_snow_temp_degC": "avg_snow_temp",
    "h2o_sat_%": "h2o_sat",
}

OUTPUT_NAMES_SNOBAL2CUSTOM = {
    "rho": "density_snow_kgm-3",
    "T_s_0": "temp_active_layer_degC",
    "T_s_l": "temp_lower_layer_degC",
    "T_s": "temp_snow_degC",
    "cc_s_0": "coldcontent_active_layer_Jm-2",
    "cc_s_l": "coldcontent_lower_layer_Jm-2",
    "cc_s": "coldcontent_snow_Jm-2",
    "m_s": "specific_mass_snow_kgm-2",
    "m_s_0": "specific_mass_active_layer_kgm-2",
    "m_s_l": "specific_mass_lower_layer_kgm-2",
    "z_s": "thickness_snow_m",
    "z_s_0": "thickness_active_layer_m",
    "z_s_l": "thickness_lower_layer_m",
    "h2o_sat": "h2o_sat_%",
    "layer_count": "layer_count",
    "h2o": "liquid_h2o_kgm-2",
    "h2o_max": "max_h2o_kgm-2",
    "h2o_vol": "h2o_vol_frac",
    "h2o_total": "total_h2o_kgm-2",
    "R_n_bar": "net_radiation_Wm-2",
    "H_bar": "sensible_heat_flux_Wm-2",
    "L_v_E_bar": "latent_heat_flux_Wm-2",
    "G_bar": "ground_heat_flux_Wm-2",
    "G_0_bar": "inter_layer_heat_flux_Wm-2",
    "M_bar": "advective_heat_flux_Wm-2",
    "delta_Q_bar": "delta_snow_energy_Wm-2",
    "delta_Q_0_bar": "delta_active_layer_energy_Wm-2",
    "E_s_sum": "evap_kgm-2",
    "melt_sum": "snowmelt_kgm-2",
    "ro_pred_sum": "surface_Water_input_kg",
    "current_time": "current_time",
    "time_since_out": "time_since_out",
}
