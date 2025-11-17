#include <errno.h>
#include <math.h>

#include "envphys.h"
#include "error_logging.h"

/**
Saturation vapor pressure of ice

@param tk Input temperature [K]
*/
double sati(double tk) {
    double l10;
    double x;

    if (tk <= 0.) {
        LOG_ERROR("Input temperature (tk): %f is less than zero", tk);
        exit(EXIT_FAILURE);
    }

    if (tk > FREEZE) {
        x = satw(tk);
        return (x);
    }

    errno = 0;
    l10 = log(1.e1);

    // clang-format off
    x = pow(
        1.e1,
        -9.09718 * ((FREEZE / tk) - 1.)
        - 3.56654 * log(FREEZE / tk) / l10
        + 8.76793e-1 * (1. - (tk / FREEZE))
        + log(6.1071) / l10
    );
    // clang-format on

    if (errno) {
        LOG_ERROR("Bad return from log or pow");
        exit(EXIT_FAILURE);
    }

    return (x * 1.e2);
}
