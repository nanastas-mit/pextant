#include <pybind11/pybind11.h>
#include "headers/GraphNode.h"

namespace py = pybind11;

namespace pextant
{
    // Constructors
    GraphNode::GraphNode(const GraphCoordinate& coordinate_, float gCost_)
    {
        this->coordinate = coordinate_;
        this->parentCoordinate.first = 0;
        this->parentCoordinate.second = 0;
        this->gCost = gCost_;
        this->hCost = 0.f;
    }
    GraphNode::GraphNode(const pybind11::tuple& pyCoordinate, float gCost_)
    {
        this->coordinate.first = pyCoordinate[0].cast<int>();
        this->coordinate.second = pyCoordinate[1].cast<int>();
        this->parentCoordinate.first = 0;
        this->parentCoordinate.second = 0;
        this->gCost = gCost_;
        this->hCost = 0.f;
    }
    GraphNode::GraphNode() : GraphNode(GraphCoordinate(0, 0), 0.f) {}
}