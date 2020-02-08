#ifndef ALGORITHMS_HEADER
#define ALGORITHMS_HEADER

#include <pybind11/pybind11.h>


namespace pextant
{
    pybind11::list& AstarSolve(
        pybind11::tuple& source,
        pybind11::tuple& target,
        pybind11::function& heuristic_func,
        pybind11::function& find_neighbors_func);
}

#endif
