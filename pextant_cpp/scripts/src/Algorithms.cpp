#include <assert.h>
#include <exception>
#include <pybind11/pybind11.h>
#include <queue>
#include <tuple>
#include "headers/Algorithms.h"
#include "headers/GraphNode.h"
#include "headers/Utils.h"


namespace py = pybind11;

namespace pextant
{
    const int G_COST_PAIR_INDEX = 0;
    const int H_COST_PAIR_INDEX = 0;

    py::tuple GraphCoordinateToPyTuple(const GraphCoordinate& coordinate)
    {
        return pybind11::make_tuple(coordinate.first, coordinate.second);
    }

    py::list& AstarSolve(
        py::tuple& source,
        py::tuple& target,
        py::function& heuristic_func,
        py::function& find_neighbors_func)
    {
        // convert source and target to c++ objects
        GraphNode sourceNode(source, 0.f);
        GraphNode targetNode(target, 0.f);

        // if source and target are the same, return trivial solution immediately
        if (sourceNode == targetNode)
        {
            auto path = new py::list();
            path->append(target);
            return *path;
        }

        // PRIORITY QUEUE q:
        //   create queue for determining which nodes to process next.
        //   queue is sorted by f-value, smallest to largest.
        //   f-value is sum of the cost needed to get to node from source (known to be min at queue-add time)
        //     and expected 'heuristic' cost needed to get to target (a 'best guess')
        std::priority_queue<GraphNode, std::vector<GraphNode>, GraphNode::PriorityQueueSortFunction> q;

        // MAP explored:
        //  create dictionary for tracking which nodes are in the closed set.
        //  key is node in closed set, value is that node's parent.
        std::unordered_map<GraphCoordinate, GraphCoordinate, GraphNode::CoordinateHashFunction> explored;

        // MAP enqueued:
        //   keeps track of what nodes have ever been on the queue (i.e. looked at in any capacity).
        //   useful for caching hCost (never changes) and keeping track of min all-time gCost
        //     => only needed as part of an optimization (fewer priority queue inserts)
        std::unordered_map<GraphCoordinate, std::pair<float, float>, GraphNode::CoordinateHashFunction> enqueued;

        // add source to queue and begin
        q.push(sourceNode);
        while (!q.empty())
        {
            // remove node with smallest F-value
            GraphNode currentNode = q.top();
            q.pop();

            // if node is target (i.e. we've reached the target)
            //   => we're done!
            if (currentNode == targetNode)
            {
                // CREATE PATH:
                auto path = new py::list();

                // add the target
                path->append(target);

                // add intermediates
                GraphCoordinate currentCoordinate = currentNode.parentCoordinate;
                while (currentCoordinate != sourceNode.coordinate && explored.count(currentCoordinate))
                {
                    path->append(GraphCoordinateToPyTuple(currentCoordinate));
                    currentCoordinate = explored[currentCoordinate];
                }

                // add the source
                path->append(source);

                // reverse the path and return
                path->attr("reverse")();
                return *path;
            }
            // otherwise, if node is already explored (i.e. already in the closed set, already has min cost path)
            //   => continue on
            else if (explored.count(currentNode.coordinate))
            {
                continue;
            }
            // otherwise... (not done and not already explored)
            else
            {
                // add node to explored (i.e. closed set)
                explored[currentNode.coordinate] = currentNode.parentCoordinate;

                // go through all neighbors
                py::list neighbors = find_neighbors_func(GraphCoordinateToPyTuple(currentNode.coordinate)).cast<py::list>();
                for (auto neighborWithCost : neighbors)
                {
                    // construct new node for this neighbor
                    auto neighborCoordinate = neighborWithCost.cast<py::tuple>()[0].cast<py::tuple>();
                    auto costFromCurrentNode = neighborWithCost.cast<py::tuple>()[1].cast<float>();
                    GraphNode neighborNode(neighborCoordinate, currentNode.gCost + costFromCurrentNode);

                    // if neighbor already explored (i.e. in closed set)
                    //   => continue on
                    if (explored.count(neighborNode.coordinate))
                    {
                        continue;
                    }

                    // if node has even been on the queue
                    //   => get cached hCost (will always be the same) and current gCost (might change)
                    float hCost;
                    if (enqueued.count(neighborNode.coordinate))
                    {
                        // get old gCost and current hCost from cache
                        auto gCosthCostPair = enqueued[neighborNode.coordinate];
                        float oldGCost = std::get<G_COST_PAIR_INDEX>(gCosthCostPair);
                        hCost = std::get<H_COST_PAIR_INDEX>(gCosthCostPair);

                        // if whatever is currently on queue has lower gCost than what we just found
                        //   => don't bother adding it again (we know path through current to neighbor is worse than what has already been found)
                        if (neighborNode.gCost >= oldGCost)
                        {
                            continue;
                        }
                    }
                    // otherwise... (we've never seen this node before!)
                    else
                    {
                        // determine hCost
                        hCost = heuristic_func(GraphCoordinateToPyTuple(neighborNode.coordinate)).cast<float>();
                    }

                    // set neighbor's cost and parent values
                    neighborNode.hCost = hCost;
                    neighborNode.parentCoordinate = currentNode.coordinate;

                    // update cache and add to queue
                    enqueued[neighborNode.coordinate] = std::make_pair(neighborNode.gCost, hCost);
                    q.push(neighborNode);
                }
            }
        }

        // return the constructed path
        return *(new py::list());
    }
}