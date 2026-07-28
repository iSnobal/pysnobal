#ifndef ERROR_LOGGING_H
#define ERROR_LOGGING_H

#include <stdio.h>
#include <stdlib.h>

// Macro to print a custom message to stderr
#define LOG_ERROR(message, ...) \
    fprintf(stderr, "[%s:%d] ERROR: " message "\n", __FILE__, __LINE__, ##__VA_ARGS__)


// Needed here to compile, but defined in print_backtrace.c
void print_user_backtrace(void);

/* Show stacktrace logging and exit */
#define EXIT_WITH_TRACE(status) do {                                       \
    fprintf(stderr, "[FATAL] Exit called at %s:%d\n", __FILE__, __LINE__); \
    print_user_backtrace();                                                \
    exit(status);                                                          \
} while(0)

#endif // ERROR_LOGGING_H
