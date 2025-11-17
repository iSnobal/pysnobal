/*
 ** NAME
 **      _h_le -- calculates turbulent transfer at a point
 **
 ** DESCRIPTION
 **      Calculates point turbulent transfer (H and L_v_E) for a 2-layer
 **      snowcover.
 **
 ** GLOBAL VARIABLES READ
 **
 ** GLOBAL VARIABLES MODIFIED
 **
 */

#include "_snobal.h"
#include "envphys.h"
#include "error_logging.h"

int _h_le(void) {
    // Saturation Vapor Pressure at surface temperature
    double e_s;
    // Saturation Vapor Pressure at air temperature
    double sat_vp;
    // Relative temperature measurement height above snow surface
    double rel_z_T;
    // Relative wind speed measurement height above snow surface
    double rel_z_u;
    LoopResult hle1_result;

    // Calculate saturation vapor pressure
    e_s = sati(T_s_0);
    if (e_s == FALSE)
        return FALSE;

    // Error check for vapor pressures
    sat_vp = sati(T_a);
    if (sat_vp == FALSE)
        return FALSE;
    if (e_a > sat_vp) {
        e_a = sat_vp;
    }

    // Determine if heights are relative or absolute
    if (relative_hts) {
        rel_z_T = z_T;
        rel_z_u = z_u;
    } else {
        rel_z_T = z_T - z_s;
        rel_z_u = z_u - z_s;
    }

    // Calculate H & L_v_E
    hle1_result = hle1(P_a, T_a, T_s_0, rel_z_T, e_a, e_s, rel_z_T, u, rel_z_u, z_0, &H, &L_v_E, &E);
    if (hle1_result.return_code != 0) {
        LOG_ERROR(
            "hle1 did not converge \n"
            "Air Pressure (P_a): %f \n "
            "Air Temperature (T_a): %f \t "
            "Snow Surface Temperature (T_s_0): %f \n "
            "Vapor Pressure (e_a): %f \t "
            "Saturation Vapor Pressure (e_s): %f \n "
            "Wind Speed (u): %f \n"
            "last difference: %f",
            P_a, T_a, T_s_0, e_a, e_s, u, z_0, hle1_result.remainder
        );

        return FALSE;
    }

    return TRUE;
}
