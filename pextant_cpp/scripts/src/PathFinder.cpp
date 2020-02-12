#include <assert.h>
#include <exception>
#include <queue>
#include <tuple>
#include "headers/PathFinder.h"
#include "headers/Utils.h"


namespace py = pybind11;

namespace pextant
{
    py::list& PathFinder::AstarSolve(py::tuple source, py::tuple target)
    {
        // if nothing cached, early out
        if (!_cached)
        {
            // return an empty path
            printf("No Data Cached - returning");
            return *(new py::list());
        }

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

        // add source to queue and begin
        _q.push(sourceNode);
        while (!_q.empty())
        {
            // remove node with smallest F-value
            GraphNode currentNode = _q.top();
            _q.pop();

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
                while (currentCoordinate != sourceNode.coordinate && _explored.count(currentCoordinate))
                {
                    path->append(GraphCoordinateToPyTuple(currentCoordinate));
                    currentCoordinate = _explored[currentCoordinate];
                }

                // add the source
                path->append(source);

                // reverse the path and return
                path->attr("reverse")();
                return *path;
            }
            // otherwise, if node is already explored (i.e. already in the closed set, already has min cost path)
            //   => continue on
            else if (_explored.count(currentNode.coordinate))
            {
                continue;
            }
            // otherwise... (not done and not already explored)
            else
            {
                // add node to explored (i.e. closed set)
                _explored[currentNode.coordinate] = currentNode.parentCoordinate;

                // go through all neighbors
                for (int iKernel = 0; iKernel < _kernel.size(); iKernel++)
                {
                    // get reference to neighbor
                    GraphNode neighborNode;
                    float toNeighborCost;
                    if (!TryGetNeighborAtKernelIndex(currentNode, iKernel, neighborNode, toNeighborCost))
                    {
                        continue;
                    }
                    neighborNode.gCost = toNeighborCost + currentNode.gCost;

                    // if neighbor already explored (i.e. in closed set)
                    //   => continue on
                    if (_explored.count(neighborNode.coordinate))
                    {
                        continue;
                    }

                    // if node has ever been on the queue
                    //   => get cached hCost (will always be the same) and current gCost (might change)
                    float hCost;
                    if (_enqueued.count(neighborNode.coordinate))
                    {
                        // get old gCost and current hCost from cache
                        auto gCosthCostPair = _enqueued[neighborNode.coordinate];
                        float oldGCost = gCosthCostPair.first;
                        hCost = gCosthCostPair.second;

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
                        hCost = GetNodeHeuristic(neighborNode);
                    }

                    // set neighbor's cost and parent values
                    neighborNode.hCost = hCost;
                    neighborNode.parentCoordinate = currentNode.coordinate;

                    // update cache and add to queue
                    _enqueued[neighborNode.coordinate] = std::make_pair(neighborNode.gCost, hCost);
                    _q.push(neighborNode);
                }
            }
        }

        // return an empty path
        return *(new py::list());
    }

    void PathFinder::PrepareCache(
        py::list& to_neighbor_costs,
        py::list& obstacle_map,
        py::list& to_goal_heuristics,
        py::list& kernel)
    {
        // set kernel
        auto kernelSize = static_cast<int>(py::len(kernel));
        assert(kernelSize == GraphNodeCachedDatum::KERNEL_SIZE);
        printf("kernelSize = %d\n", kernelSize);
        _kernel = std::vector<GraphCoordinate>(kernelSize);
        for (int iKernel = 0; iKernel < kernelSize; iKernel++)
        {
            auto py_coord = kernel[iKernel].cast<py::list>();
            _kernel[iKernel] = GraphCoordinate(py_coord[0].cast<int>(), py_coord[1].cast<int>());
        }

        // determine row and column counts
        auto rowCount = static_cast<int>(py::len(to_neighbor_costs));
        assert(rowCount > 0 && rowCount == py::len(obstacle_map) && rowCount == py::len(to_goal_heuristics));
        printf("rowCount = %d\n", rowCount);
        auto columnCount = static_cast<int>(py::len(to_neighbor_costs[0]));
        assert(columnCount > 0 && columnCount == py::len(obstacle_map[0]) && columnCount == py::len(to_goal_heuristics[0]));
        printf("columnCount = %d\n", columnCount);
        _gridSize = std::pair<int, int>(rowCount, columnCount);

        // create matrix of node data
        _cachedNodeData = NodeDataMatrix(rowCount, std::vector<GraphNodeCachedDatum>(columnCount));
        for (int row = 0; row < rowCount; row++)
        {
            auto py_heuristics_row = to_goal_heuristics[row].cast<py::list>();
            auto py_costs_row = to_neighbor_costs[row].cast<py::list>();
            auto obstacles_row = obstacle_map[row].cast<py::list>();
            for (int col = 0; col < columnCount; col++)
            {
                GraphNodeCachedDatum& datum = _cachedNodeData[row][col];

                // set heuristic
                datum.heuristic = py_heuristics_row[col].cast<float>();

                // set obstacle status
                datum.isObstacle = obstacles_row[col].cast<bool>();

                // set neighbor costs
                auto py_costs_list = py_costs_row[col].cast<py::list>();
                for (int iKernel = 0; iKernel < GraphNodeCachedDatum::KERNEL_SIZE; iKernel++)
                {
                    datum.toNeighborCosts[iKernel] = py_costs_list[iKernel].cast<float>();
                }
            }
        }

        // note that we are cached
        _cached = true;
    }

    bool PathFinder::TryGetNeighborAtKernelIndex(
        const GraphNode & node,
        int kernelIndex,
        GraphNode& outNeighbor,
        float& outCost) const
    {
        // make sure index is in bounds
        if (kernelIndex < 0 || kernelIndex >= _kernel.size())
        {
            return false;
        }

        // construct neighbor
        auto offset = _kernel.at(kernelIndex);
        outNeighbor.coordinate = GraphCoordinate(
            node.coordinate.first + offset.first,
            node.coordinate.second + offset.second
        );

        // check to see if neighbor is in bounds
        if (outNeighbor.coordinate.first < 0 || outNeighbor.coordinate.first >= _gridSize.first ||
            outNeighbor.coordinate.second < 0 || outNeighbor.coordinate.second >= _gridSize.second)
        {
            return false;
        }

        // check to see if neighbor is obstacle
        if (_cachedNodeData[outNeighbor.coordinate.first][outNeighbor.coordinate.second].isObstacle)
        {
            outCost = -1.f;
            return false;
        }

        // a valid neighbor!
        outCost = _cachedNodeData[node.coordinate.first][node.coordinate.second].toNeighborCosts[kernelIndex];
        return true;
    }

    float PathFinder::GetNodeHeuristic(const GraphNode& node) const
    {
        // assert we're in bounds to see if coordinate is in bounds
        assert(node.coordinate.first >= 0 && node.coordinate.first < _gridSize.first &&
            node.coordinate.second >= 0 && node.coordinate.second < _gridSize.second);

        // return the heuristic
        return _cachedNodeData[node.coordinate.first][node.coordinate.second].heuristic;
    }
}