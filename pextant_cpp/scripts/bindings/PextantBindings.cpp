#include <pybind11/pybind11.h>
#include <pybind11/embed.h>
#include "headers/Algorithms.h"
#include "headers/Tests.h"

namespace py = pybind11;

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

    // astar return test
    m.def(
        "test_astar_return",
        &pextant::TestAstarReturn,
        py::return_value_policy::take_ownership,
        "tests the return type of astar_solve"
    );

    // heuristic fn passing
    m.def(
        "test_heuristic_function_passing",
        &pextant::TestHeuristicFunctionPassing,
        "tests passing of a heuristic fn"
    );

    // astar arg test
    m.def(
        "test_astar_args",
        &pextant::TestAstarArgs,
        "tests astar_solve argument passing"
    );

    // do_astar
    m.def(
        "astar_solve",
        &pextant::AstarSolve,
        py::return_value_policy::take_ownership,
        R"pbdoc(
            astar function
        )pbdoc"
    );

#ifdef VERSION_INFO
    m.attr("__version__") = VERSION_INFO;
#else
    m.attr("__version__") = "dev";
#endif
}