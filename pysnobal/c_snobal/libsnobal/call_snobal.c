/*
 * call_snobal.c
 * Takes input from a Python function and calls all the necessary C functions
 */

#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <string.h>

// clang-format off
#include "snobal.h"
#include "envphys.h"
#include "pysnobal.h"
#include "error_logging.h"
// clang-format on

int call_snobal(
    int N,
    int nthreads,
    int first_step,
    TSTEP_REC tstep[4],
    INPUT_REC_ARR *input1,
    INPUT_REC_ARR *input2,
    PARAMS params,
    OUTPUT_REC_ARR *output1
) {
    int n;

    /* set threads */
    if (nthreads != 1) {
        omp_set_num_threads(nthreads);
    }

#pragma omp threadprivate(tstep_info)
    for (n = 0; n < 4; n++)
        tstep_info[n] = tstep[n];

    // Pull out the parameters
    z_u = params.z_u;
    z_T = params.z_T;
    z_g = params.z_g;
    relative_hts = params.relative_heights;
    max_z_s_0 = params.max_z_s_0;
    max_h2o_vol = params.max_h2o_vol;

#pragma omp parallel shared(output1, input1, input2, first_step) private(n) \
    copyin(tstep_info, z_u, z_T, z_g, relative_hts, max_z_s_0, max_h2o_vol)
    {
#pragma omp for schedule(dynamic, 100)
        for (n = 0; n < N; n++) {

            // if (output_rec[n]->masked == 1) {
            if (output1->masked[n] == 1) {

                /*
                 * Initialize some global variables for 'snobal' library for
                 * each pass since the routine 'do_data_tstep' modifies them
                 */

                current_time = output1->current_time[n];
                time_since_out = output1->time_since_out[n];

                // The input records
                input_rec1.I_lw = input1->I_lw[n];
                input_rec1.T_a = input1->T_a[n];
                input_rec1.e_a = input1->e_a[n];
                input_rec1.u = input1->u[n];
                input_rec1.T_g = input1->T_g[n];
                input_rec1.S_n = input1->S_n[n];

                input_rec2.I_lw = input2->I_lw[n];
                input_rec2.T_a = input2->T_a[n];
                input_rec2.e_a = input2->e_a[n];
                input_rec2.u = input2->u[n];
                input_rec2.T_g = input2->T_g[n];
                input_rec2.S_n = input2->S_n[n];

                // Precip inputs
                m_pp = input1->m_pp[n];
                percent_snow = input1->percent_snow[n];
                rho_snow = input1->rho_snow[n];
                T_pp = input1->T_pp[n];

                precip_now = 0;
                if (m_pp > 0)
                    precip_now = 1;

                // Extract data from I/O buffers
                double elevation = output1->elevation[n];

                z_0 = output1->z_0[n];
                z_s = output1->z_s[n];
                rho = output1->rho[n];

                T_s_0 = output1->T_s_0[n];
                T_s_l = output1->T_s_l[n];
                T_s = output1->T_s[n];
                h2o_sat = output1->h2o_sat[n];
                layer_count = output1->layer_count[n];

                R_n_bar = output1->R_n_bar[n];
                H_bar = output1->H_bar[n];
                L_v_E_bar = output1->L_v_E_bar[n];
                G_bar = output1->G_bar[n];
                M_bar = output1->M_bar[n];
                delta_Q_bar = output1->delta_Q_bar[n];
                E_s_sum = output1->E_s_sum[n];
                melt_sum = output1->melt_sum[n];
                ro_pred_sum = output1->ro_pred_sum[n];

                // Establish conditions for snowpack
                if (first_step == 1) {
                    init_snow();
                    R_n_bar = 0.0;
                    H_bar = 0.0;
                    L_v_E_bar = 0.0;
                    G_bar = 0.0;
                    M_bar = 0.0;
                    delta_Q_bar = 0.0;
                    E_s_sum = 0.0;
                    melt_sum = 0.0;
                    ro_pred_sum = 0.0;
                } else {
                    init_snow();
                }

                // Set air pressure from site elevation
                P_a = HYSTAT(
                    SEA_LEVEL,
                    STD_AIRTMP,
                    STD_LAPSE,
                    (output1->elevation[n] / 1000.0),
                    GRAVITY,
                    MOL_AIR
                );

                /************************************
                 * Run model on data for this pixel *
                 ************************************/
                if (!do_data_tstep())
                    LOG_ERROR("Error processing pixel %d", n);

                output1->current_time[n] = current_time;
                output1->time_since_out[n] = time_since_out;

                output1->rho[n] = rho;
                output1->T_s_0[n] = T_s_0;
                output1->T_s_l[n] = T_s_l;
                output1->T_s[n] = T_s;
                output1->h2o_sat[n] = h2o_sat;
                output1->h2o_max[n] = h2o_max;
                output1->h2o[n] = h2o;
                output1->h2o_vol[n] = h2o_vol;
                output1->h2o_total[n] = h2o_total;
                output1->layer_count[n] = layer_count;
                output1->cc_s_0[n] = cc_s_0;
                output1->cc_s_l[n] = cc_s_l;
                output1->cc_s[n] = cc_s;
                output1->m_s_0[n] = m_s_0;
                output1->m_s_l[n] = m_s_l;
                output1->m_s[n] = m_s;
                output1->z_0[n] = z_0;
                output1->z_s_l[n] = z_s_l;
                output1->z_s_0[n] = z_s_0;
                output1->z_s[n] = z_s;

                output1->R_n_bar[n] = R_n_bar;
                output1->H_bar[n] = H_bar;
                output1->L_v_E_bar[n] = L_v_E_bar;
                output1->G_bar[n] = G_bar;
                output1->G_0_bar[n] = G_0_bar;
                output1->M_bar[n] = M_bar;
                output1->delta_Q_bar[n] = delta_Q_bar;
                output1->delta_Q_0_bar[n] = delta_Q_0_bar;
                output1->E_s_sum[n] = E_s_sum;
                output1->melt_sum[n] = melt_sum;
                output1->ro_pred_sum[n] = ro_pred_sum;
            }
        } /* for loop on grid */
    }

    return -1;
}
