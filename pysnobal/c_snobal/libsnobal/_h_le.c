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
    if (hle1(P_a, T_a, T_s_0, rel_z_T, e_a, e_s, rel_z_T, u, rel_z_u, z_0, &H, &L_v_E, &E) != 0) {
        LOG_ERROR(
            "hle1 did not converge \n"
            "P_a: %f \n "
            "T_a: %f \n "
            "T_s_0: %f "
            "e_a: %f "
            "e_s: %f "
            "u: %f",
            P_a, T_a, T_s_0, e_a, e_s, u, z_0
        );

        return FALSE;
    }

    return TRUE;
}
