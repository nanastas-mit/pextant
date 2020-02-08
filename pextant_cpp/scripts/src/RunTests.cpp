#include <pybind11/pybind11.h>
#include <pybind11/embed.h>
#include <iostream>
#include "headers/Algorithms.h"
#include "headers/Tests.h"


namespace py = pybind11;


int main()
{
    printf("Hello World!\n\n");

    py::scoped_interpreter guard{}; // start the interpreter and keep it alive

    // import our modules
    py::module pextant_cpp = py::module::import("pextant_cpp");
    py::module sys = py::module::import("sys");
    py::module test_functions = py::module::import("cpp_test_helper.test_functions");

    // basic funcitonality tests
    pextant::TestRandoms();
    pextant::TestPriorityQueue();
    pextant::TestPyList();
    auto astar_test_return = pextant_cpp.attr("test_astar_return")();
    py::function h_m = test_functions.attr("test_heuristic_manhattan");
    pextant::TestHeuristicFunctionPassing(0, 0, h_m);
    pextant::TestHeuristicFunctionPassing(0, 0, h_e);

    // astar test
    py::function astar_solve = pextant_cpp.attr("astar_solve");
    auto source = py::make_tuple(0, 0); // whatever you want
    auto target = py::make_tuple(7, 5); // whatever you want
    py::function h_e = test_functions.attr("test_heuristic_euclidean");
    py::function find_neighbors = test_functions.attr("test_get_neighbors_and_cost");
    auto astar_return = astar_solve(source, target, h_e, find_neighbors);

    printf("\n\nGoodbye, World!");
}
