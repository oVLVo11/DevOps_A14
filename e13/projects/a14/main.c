#include <stdio.h>
#include "config.h"
#include "adjustment.h"

int helper(void);

int main(void) {
    printf("%d\n", BASE + helper() + ADJUSTMENT);
    return 0;
}
