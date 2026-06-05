#ifndef ERROR_LOGGING_H
#define ERROR_LOGGING_H

#include <stdio.h>
#include <stdlib.h>

// Macro to print a custom message to stderr
#define LOG_ERROR(message, ...) \
    fprintf(stderr, "[%s:%d] ERROR: " message "\n", __FILE__, __LINE__, ##__VA_ARGS__)

#endif // ERROR_LOGGING_H
