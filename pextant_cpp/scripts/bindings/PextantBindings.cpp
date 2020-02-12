#include <pybind11/pybind11.h>
#include <pybind11/embed.h>
#include "headers/Algorithms.h"
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

    // do_astar
    m.def(
        "astar_solve",
        &AstarSolve,
        py::return_value_policy::take_ownership,
        R"pbdoc(
            astar function
        )pbdoc"
    );

    // pathfinder class
    py::class_<PathFinder> pathFinder(m, "PathFinder");
    pathFinder.def(py::init())
        .def(py::init<PathFinder::Type>())
        .def_property_readonly("finderType", &PathFinder::getFinderType)
        .def_property_readonly("cached", &PathFinder::getCached)
        .def("astar_solve", &PathFinder::AstarSolve)
        .def("astar_step", &PathFinder::AstarStep)
        .def("prepare_cache", &PathFinder::PrepareCache)
        .def("clear_cache", &PathFinder::ClearCache)
        .def("reset_progress", &PathFinder::ResetProgress)
        .def("get_astar_result", &PathFinder::GetAstarResult);
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