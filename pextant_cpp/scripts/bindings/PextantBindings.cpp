#include <pybind11/pybind11.h>
#include <pybind11/embed.h>
#include "headers/PathFinder.h"

namespace py = pybind11;
using namespace pextant;

#ifdef PEXTANT_DEBUGGING_EXECUTABLE
PYBIND11_EMBEDDED_MODULE(pextant_cpp, m)
#else // PEXTANT_DEBUGGING_EXECUTABLE
PYBIND11_MODULE(pextant_cpp, m)
#endif
{
    // Module
    m.doc() = R"pbdoc(
        C++ extension module with classes/functions for PEXTANT
        -----------------------

        .. currentmodule:: pextant_cpp
    )pbdoc";

    // pathfinder class
    py::class_<PathFinder> pathFinder(m, "PathFinder");
    pathFinder.def(py::init())
        .def(py::init<PathFinder::Type>())
        .def_property_readonly("finder_type", &PathFinder::getFinderType)
        .def_property_readonly("costs_cached", &PathFinder::getCostsCached)
        .def_property_readonly("obstacles_cached", &PathFinder::getObstaclesCached)
        .def_property_readonly("heuristics_cached", &PathFinder::getHeuristicsCached)
        .def_property_readonly("all_cached", &PathFinder::getAllCached)
        .def("astar_solve", &PathFinder::AstarSolve)
        .def("set_kernel", &PathFinder::SetKernel)
        .def("clear_kernel", &PathFinder::ClearKernel)
        .def("cache_costs", &PathFinder::CacheToNeighborCosts)
        .def("clear_costs", &PathFinder::ClearToNeighborCosts)
        .def("cache_obstacles", &PathFinder::CacheObstacles)
        .def("clear_obstacles", &PathFinder::ClearObstacles)
        .def("cache_heuristics", &PathFinder::CacheToGoalHeuristics)
        .def("clear_heuristics", &PathFinder::ClearToGoalHeuristics)
        .def("clear_all", &PathFinder::ClearAll)
        .def("reset_progress", &PathFinder::ResetProgress);
    py::enum_<PathFinder::Type>(pathFinder, "Type")
        .value("dijkstra", PathFinder::Type::DIJKSTRA)
        .value("astar", PathFinder::Type::ASTAR)
        .value("dstar", PathFinder::Type::DSTAR)
        .export_values();

#ifdef VERSION_INFO
    m.attr("__version__") = VERSION_INFO;
#else
    m.attr("__version__") = "dev";
#endif
}