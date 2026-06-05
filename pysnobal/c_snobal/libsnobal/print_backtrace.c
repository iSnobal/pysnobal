#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <execinfo.h>

void print_user_backtrace(void) {
    // Number of stack frames to capture
    void *buffer[100];
    int nptrs = backtrace(buffer, 100);
    char **strings = backtrace_symbols(buffer, nptrs);

    if (strings == NULL) {
        perror("backtrace_symbols failed");
        return;
    }

    fprintf(stderr, "=== Application Stack Trace ===\n");

    for (int i = 0; i < nptrs; i++) {
        // Skip this function to keep the logs clean
        if (strstr(strings[i], "print_user_backtrace") != NULL) {
            continue;
        }

        // Only log frames from your application binary
        if (strstr(strings[i], "snobal") != NULL) {
            fprintf(stderr, "%s\n", strings[i]);
        }
    }

    free(strings);
}
