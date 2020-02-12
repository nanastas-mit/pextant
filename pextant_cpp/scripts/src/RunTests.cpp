#include <pybind11/pybind11.h>
#include <pybind11/embed.h>
#include <iostream>
#include "headers/Algorithms.h"
#include "headers/Tests.h"
#include "headers/PathFinder.h"


namespace py = pybind11;


int main()
{
    printf("Hello World!\n\n");

    py::scoped_interpreter guard{}; // start the interpreter and keep it alive

    // import our modules
    py::module pextant_cpp = py::module::import("pextant_cpp");
    py::module sys = py::module::import("sys");
    py::module test_functions = py::module::import("cpp_test_helper.test_functions");

    // setup target and source
    py::function find_target = test_functions.attr("find_target");
    auto target = find_target().cast<py::tuple>();
    auto source = py::make_tuple(0, 0); // whatever you want


    // get cacheable maps
    py::function get_cost_map = test_functions.attr("create_costs_map");
    py::list cost_map = get_cost_map();
    py::function create_obstacle_map = test_functions.attr("create_obstacle_map");
    py::list obstacle_map = create_obstacle_map();
    py::function get_heuristic_map = test_functions.attr("create_heuristic_map");
    py::list h_map = get_heuristic_map();
    py::list kernel = test_functions.attr("test_kernel");

    // astar test
    auto finder = pextant::PathFinder();
    finder.PrepareCache(cost_map, obstacle_map, h_map, kernel)
    py::list& path = finder.AstarSolve(source, target);

    printf("\n\nGoodbye, World!");
}
