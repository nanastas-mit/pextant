#ifndef TESTS_HEADER
#define TESTS_HEADER

#include <pybind11/pybind11.h>

namespace pextant
{
    void TestRandoms();

    void TestPriorityQueue();

    void TestPyList();

    pybind11::list& TestAstarReturn();

    void TestHeuristicFunctionPassing(int x, int y, pybind11::function& heuristic);

    void TestAstarArgs(
        pybind11::tuple& source,
        pybind11::tuple& target,
        pybind11::function& heuristic_func,
        pybind11::function& find_neighbors_func);
}

#endif // !TESTS_HEADER
