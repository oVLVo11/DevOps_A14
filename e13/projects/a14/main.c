#include <stdio.h>
#include "config.h"

int helper(void);

int main(void) {
    printf("%d\n", BASE + helper());
    return 0;
}
