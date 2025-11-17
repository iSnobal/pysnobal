#include <errno.h>
#include <math.h>

#include "envphys.h"
#include "error_logging.h"

/**
Saturation water vapor pressure of water

@param tk Air temperature [K]
*/
double satw(double tk) {
    double x;
    double l10;

    if (tk <= 0.) {
        LOG_ERROR("Input temperature (tk): %f is less than zero", tk);
        exit(EXIT_FAILURE);
    }

    errno = 0;
    l10 = log(1.e1);

    // clang-format off
    x = pow(
      1.e1,
      -7.90298 * (BOIL / tk - 1.)
      + 5.02808 * log(BOIL / tk) / l10
      - 1.3816e-7 * (pow(1.e1, 1.1344e1 * (1. - tk / BOIL)) - 1.)
      + 8.1328e-3 * (pow(1.e1, -3.49149 * (BOIL / tk - 1.)) - 1.)
      + log(SEA_LEVEL) / l10
    );
    // clang-format off

    if (errno) {
        LOG_ERROR("Bad return from log or pow");
        exit(EXIT_FAILURE);
    }

    return (x);
}
