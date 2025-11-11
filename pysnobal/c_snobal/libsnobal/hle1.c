/**
Sensible and latent heat fluxes at one height

Computes sensible and latent heat flux and mass flux given measurements of temperature
and specific humidity at surface and one height, wind speed at one height, and
roughness length.
The temperature, humidity, and wind speed measurements need not all be at the same height.

See also:
  Brutsaert, W., 1982. Evaporation Into the Atmosphere, D. Reidel, Hingham, Mass, 299 pp.
*/

#include <math.h>

#include "envphys.h"
#include "error_logging.h"

const double AH = 1.0;         /* ratio sensible/momentum phi func	*/
const double AV = 1.0;         /* ratio latent/momentum phi func	*/
const int MAX_ITERATIONS = 50; /* max # iterations allowed		*/
const double PAESCHKE = 7.35;  /* Paeschke's const (eq. 5.3)		*/
const double THRESH = 1.e-5;   /* convergence threshold		*/

// PSI functions types
typedef enum {
    FLUX_MOMENTUM = 0, // Sensible/Momentum
    FLUX_SENSIBLE = 1, // Sensible heat flux
    FLUX_LATENT = 2    // Latent heat flux
} FluxType;

const double BETA_S = 5.2;
const double BETA_U = 16.0;

/*
Equations 4.92

@param zeta z/lo
@param code One of the code options from above constants
@return psi-function value
*/
static double psi(double zeta, FluxType type) {
    double x; // height function variable
    double result;

    // Stable case
    if (zeta > 0) {
        if (zeta > 1)
            zeta = 1;
        result = -BETA_S * zeta;
    }
    // Unstable case
    else if (zeta < 0) {

        x = sqrt(sqrt(1 - BETA_U * zeta));

        switch (type) {
            case FLUX_MOMENTUM:
                result = 2 * log((1 + x) / 2) + log((1 + x * x) / 2) - 2 * atan(x) + M_PI_2;
                break;

            case FLUX_SENSIBLE:
            case FLUX_LATENT:
                result = 2 * log((1 + x * x) / 2);
                break;

            default:
                LOG_ERROR("Invalid PSI-function code passed in: %i", type);
                exit(EXIT_FAILURE);
        }
    }
    // Neutral case
    else {
        result = 0;
    }

    return result;
}

LoopResult hle1(
    double press, /* air pressure (Pa)			*/
    double ta,    /* air temperature (K) at height za	*/
    double ts,    /* surface temperature (K)		*/
    double za,    /* height of air temp measurement (m)	*/
    double ea,    /* vapor pressure (Pa) at height zq	*/
    double es,    /* vapor pressure (Pa) at surface	*/
    double zq,    /* height of spec hum measurement (m)	*/
    double u,     /* wind speed (m/s) at height zu	*/
    double zu,    /* height of wind speed measurement (m)	*/
    double z0,    /* roughness length (m)			*/
    /* output variables */
    double *h,  /* sens heat flux (+ to surf) (W/m^2)	*/
    double *le, /* latent heat flux (+ to surf) (W/m^2)	*/
    double *e
) /* mass flux (+ to surf) (kg/m^2/s)	*/
{
    double ah = AH;
    double av = AV;
    double cp = CP_AIR;
    double d0;   // displacement height (eq. 5.3)
    double dens; // air density
    double factor;
    double g = GRAVITY;
    double k = VON_KARMAN;
    double last;  // last guess at lo
    double lo;    // Obukhov stability length (eq. 4.25)
    double ltsh;  // log ((za-d0)/z0)
    double ltsm;  // log ((zu-d0)/z0)
    double ltsv;  // log ((zq-d0)/z0)
    double qa;    // specific humidity at height zq
    double qs;    // specific humidity at surface
    double ustar; // friction velocity (eq. 4.34')
    double xlh;   // latent heat of vap/subl
    int iter;     // iteration counter

    LoopResult result = {.return_code = 0, .remainder = 0.0};

    // Check inputs
    if (z0 <= 0 || zq <= z0 || zu <= z0 || za <= z0) {
        LOG_ERROR("Configured heights not positive\n\t z0: %f \t za: %f \t zu: %f", z0, za, zu);
        result.return_code = -2;
    }

    if (ta <= 0 || ts <= 0) {
        LOG_ERROR("Temperatures are not in K\n\t ta: %f \t ts: %f", ta, ts);
        result.return_code = -2;
    }

    if (ea <= 0 || es <= 0 || press <= 0 || ea >= press || es >= press) {
        LOG_ERROR("Pressure values below 0\n\t ea: %f \t es: %f \t press: %f", ea, es, press);
        result.return_code = -2;
    }

    /* Vapor pressures can't exceed saturation vapor pressures by 25 */
    if ((es - 25.0) > sati(ts) || (ea - 25.0) > satw(ta)) {
        LOG_ERROR(
            "Vapor pressure exceeded saturation pressure\n\t es: %f \t es_sat: %f \t ea: %f \t"
            "ea_sat: %f",
            es,
            sati(ts),
            ea,
            sati(ta)
        );
        result.return_code = -2;
    }
    // Exit if there were any input errors
    if (result.return_code < 0) {
        return result;
    }

    // Adjust pressures if they were within tolerance
    if (es > sati(ts)) {
        es = sati(ts);
    }
    if (ea > satw(ta)) {
        ea = satw(ta);
    }

    // Displacement plane height, eq. 5.3 & 5.4
    d0 = 2 * PAESCHKE * z0 / 3;

    // Constant log expressions to save compute time
    ltsm = log((zu - d0) / z0);
    ltsh = log((za - d0) / z0);
    ltsv = log((zq - d0) / z0);

    // Convert vapor pressures to specific humidities
    qa = SPEC_HUM(ea, press);
    qs = SPEC_HUM(es, press);

    // Convert temperature to potential temperature
    ta += DALR * za;

    /*
     * Air density at pressure, virtual temperature of geometric mean of air and surface
     */
    dens = GAS_DEN(press, MOL_AIR, VIR_TEMP(sqrt(ta * ts), sqrt(ea * es), press));

    /*
     * Starting value - assume neutral stability, so psi-functions are all zero
     */
    ustar = k * u / ltsm;
    factor = k * ustar * dens;
    *e = (qa - qs) * factor * av / ltsv;
    *h = (ta - ts) * factor * cp * ah / ltsh;

    /*
     * If not neutral stability, iterate on Obukhov stability length to find solution
     * Follows Chapter 4.2 in Brutsaert, 1982
     */
    iter = 0;
    if (ta != ts) {

        lo = HUGE_VAL;

        do {
            last = lo;

            /*
             * Eq 4.25, but no minus sign as we define positive H as toward surface
             *
             * There was an error in the old version of this line that omitted the cubic power of
             * ustar. Now, this error has been fixed.
             */
            lo = ustar * ustar * ustar * dens / (k * g * (*h / (ta * cp) + 0.61 * *e));

            // Friction velocity, eq. 4.34'
            ustar = k * u / (ltsm - psi(zu / lo, FLUX_MOMENTUM));

            // Evaporative flux, eq. 4.33'
            factor = k * ustar * dens;
            *e = (qa - qs) * factor * av / (ltsv - psi(zq / lo, FLUX_LATENT));

            // Sensible heat flux, eq. 4.35' with sign reversed
            *h = (ta - ts) * factor * ah * cp / (ltsh - psi(za / lo, FLUX_SENSIBLE));

            result.remainder = last - lo;

        } while (fabs(result.remainder) > THRESH && fabs(result.remainder / lo) > THRESH
                 && ++iter < MAX_ITERATIONS);
    }

    result.return_code = (iter >= MAX_ITERATIONS) ? -1 : 0;

    xlh = LH_VAP(ts);
    if (ts <= FREEZE)
        xlh += LH_FUS(ts);

    // Latent heat flux (- away from surf)
    *le = xlh * *e;

    return result;
}
