#include <random>
#include "headers/Utils.h"

namespace pextant
{
    // function for getting random float in range [lower, upper]
    float RandBetweenF(float lower, float upper)
    {
        // swap upper and lower if necessary
        if (upper < lower)
        {
            upper = upper + lower;
            lower = upper - lower;
            upper = upper - lower;
        }

        float zeroToOne = static_cast<float>(std::rand()) / static_cast<float>(RAND_MAX);
        return zeroToOne * (upper - lower) + lower;
    }

    // function for getting random int in range [lower, upper)
    int RandBetweenI(int lower, int upper)
    {
        // swap upper and lower if necessary
        if (upper < lower)
        {
            upper = upper + lower;
            lower = upper - lower;
            upper = upper - lower;
        }

        int range = upper - lower;
        int randInRange = std::rand() % range;

        return randInRange + lower;
    }
}