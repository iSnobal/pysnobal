/*
 ** NAME
 **      _e_bal -- calculates point energy budget for 2-layer snowcover
 **
 ** SYNOPSIS
 **      #include "_snobal.h"
 **
 **      int
 **	_e_bal(void)
 **
 ** DESCRIPTION
 **      Calculates point energy budget for 2-layer snowcover.
 **
 ** RETURN VALUE
 **
 **	TRUE	The calculations were completed.
 **	FALSE	An error occurred
 **
 */

#include "_snobal.h"
#include "snow.h"

int _e_bal(void) {
    if (snowcover) {
        /**	Calculate energy transfer terms  **/
        // Net radiation
        _net_rad();

        // Calculate H, L_v_E, E as well
        if (!_h_le())
            return FALSE;

        // G & G_0 (conduction/diffusion heat transfer)
        if (layer_count == 1) {
            G = g_soil(rho, T_s_0, T_g, z_s_0, z_g, P_a);
            G_0 = G;
        } else { // layer_count == 2
            G = g_soil(rho, T_s_l, T_g, z_s_l, z_g, P_a);
            G_0 = g_snow(rho, rho, T_s_0, T_s_l, z_s_0, z_s_l, P_a);
        }

        // Calculate advection
        _advec();

        /** Sum energy balance terms **/
        // Surface energy budget
        delta_Q_0 = R_n + H + L_v_E + G_0 + M;

        // Total snowpack energy budget
        if (layer_count == 1)
            delta_Q = delta_Q_0;
        else // layer_count == 2
            delta_Q = delta_Q_0 + G - G_0;
    } else {
        R_n = 0.0;
        H = L_v_E = E = 0.0;
        G = G_0 = 0.0;
        M = 0.0;
        delta_Q = delta_Q_0 = 0.0;
    }

    return TRUE;
}
