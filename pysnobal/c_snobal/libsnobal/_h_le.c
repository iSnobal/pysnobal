/*
 ** NAME
 **      _h_le -- calculates turbulent transfer at a point
 **
 ** SYNOPSIS
 **      #include "_snobal.h"
 **
 **      int
 **	_h_le(void)
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

/**

@param e_s
@param sat_vp   Saturation vapor pressure
@param rel_z_T  Relative temperature measurement height above snow surface
@param rel_z_u  Relative wind speed measurement height above snow surface

@return
*/
int _h_le(void) {
    double e_s;
    double sat_vp;
    double rel_z_T;
    double rel_z_u;
    LoopResult hle1_result;

    /* calculate saturation vapor pressure */
    e_s = sati(T_s_0);
    if (e_s == FALSE)
        return FALSE;

    /*** error check for bad vapor pressures ***/
    sat_vp = sati(T_a);
    if (sat_vp == FALSE)
        return FALSE;
    if (e_a > sat_vp) {
        e_a = sat_vp;
    }

    /* determine relative measurement heights */
    if (relative_hts) {
        rel_z_T = z_T;
        rel_z_u = z_u;
    } else {
        rel_z_T = z_T - z_s;
        rel_z_u = z_u - z_s;
    }

    /* calculate H & L_v_E */
    hle1_result = hle1(P_a, T_a, T_s_0, rel_z_T, e_a, e_s, rel_z_T, u, rel_z_u, z_0, &H, &L_v_E, &E);
    if (hle1_result.return_code != 0) {
        LOG_ERROR(
            "hle1 did not converge \n"
            "P_a: %f \n "
            "T_a: %f \t "
            "T_s_0: %f \n "
            "e_a: %f \t "
            "e_s: %f \n "
            "u: %f \n"
            "last difference: %f",
            P_a, T_a, T_s_0, e_a, e_s, u, z_0, hle1_result.remainder
        );

        return FALSE;
    }

    return TRUE;
}
