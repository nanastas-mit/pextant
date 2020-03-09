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
        // if not everything cached, early out
        if (!getAllCached())
        {
            // return an empty path
            printf("Not all data cached - returning");
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

    void PathFinder::SetKernel(py::list& kernel)
    {
        // set kernel
        auto kernelSize = static_cast<int>(py::len(kernel));
        _kernel = std::vector<GraphCoordinate>(kernelSize);
        for (int iKernel = 0; iKernel < kernelSize; iKernel++)
        {
            auto py_coord = kernel[iKernel].cast<py::list>();
            _kernel[iKernel] = GraphCoordinate(py_coord[0].cast<int>(), py_coord[1].cast<int>());
        }
    }

    void PathFinder::CacheToNeighborCosts(pybind11::list& to_neighbor_costs)
    {
        // make sure there is a kernel
        auto kernelSize = _kernel.size();
        if (kernelSize == 0)
        {
            printf("kernel not yet set - returning");
        }

        // determine row and column counts
        auto rowCount = static_cast<int>(py::len(to_neighbor_costs));
        auto columnCount = static_cast<int>(py::len(to_neighbor_costs[0]));
        _gridSize = std::make_pair(rowCount, columnCount);

        // create cost matrix
        _cachedCostData = CostDataMatrix(rowCount, std::vector<CachedCostDatum>(columnCount));

        // populate cost matrix
        for (int iRow = 0; iRow < rowCount; iRow++)
        {
            auto py_costs_row = to_neighbor_costs[iRow].cast<py::list>();
            for (int iCol = 0; iCol < columnCount; iCol++)
            {
                CachedCostDatum& datum = _cachedCostData[iRow][iCol];
                datum.reserve(kernelSize);
                datum.clear();

                // store neighbor costs
                auto py_costs_list = py_costs_row[iCol].cast<py::list>();
                for (int iKernel = 0; iKernel < kernelSize; iKernel++)
                {
                    datum.push_back(py_costs_list[iKernel].cast<float>());
                }
            }
        }
    }

    void PathFinder::CacheObstacles(pybind11::list& obstacle_map)
    {
        // make sure gridsize is set
        if (_gridSize.first == 0 || _gridSize.second == 0)
        {
            printf("grid size not yet set (must perform cost caching first) - returning");
        }

        // get/verify row and column counts
        auto rowCount = static_cast<int>(py::len(obstacle_map));
        auto columnCount = static_cast<int>(py::len(obstacle_map[0]));
        assert(_gridSize.first == rowCount && _gridSize.second == columnCount);

        // create obstacle matrix
        _cachedObstacleData = ObstacleDataMatrix(rowCount, std::vector<bool>(columnCount));

        // populate obstacle matrix
        for (int iRow = 0; iRow < rowCount; iRow++)
        {
            auto py_obstacles_row = obstacle_map[iRow].cast<py::list>();
            for (int iCol = 0; iCol < columnCount; iCol++)
            {
                _cachedObstacleData[iRow][iCol] = py_obstacles_row[iCol].cast<bool>();
            }
        }
    }

    void PathFinder::CacheToGoalHeuristics(pybind11::list& to_goal_heuristics)
    {
        // make sure gridsize is set
        if (_gridSize.first == 0 || _gridSize.second == 0)
        {
            printf("grid size not yet set (must perform cost caching first) - returning");
        }

        // get/verify row and column counts
        auto rowCount = static_cast<int>(py::len(to_goal_heuristics));
        auto columnCount = static_cast<int>(py::len(to_goal_heuristics[0]));
        assert(_gridSize.first == rowCount && _gridSize.second == columnCount);

        // create obstacle matrix
        _cachedHeuristicData = HeuristicDataMatrix(rowCount, std::vector<float>(columnCount));

        // populate obstacle matrix
        for (int iRow = 0; iRow < rowCount; iRow++)
        {
            auto py_obstacles_row = to_goal_heuristics[iRow].cast<py::list>();
            for (int iCol = 0; iCol < columnCount; iCol++)
            {
                _cachedHeuristicData[iRow][iCol] = py_obstacles_row[iCol].cast<float>();
            }
        }
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
        if (_cachedObstacleData[outNeighbor.coordinate.first][outNeighbor.coordinate.second])
        {
            outCost = -1.f;
            return false;
        }

        // a valid neighbor!
        outCost = _cachedCostData[node.coordinate.first][node.coordinate.second][kernelIndex];
        return true;
    }

    float PathFinder::GetNodeHeuristic(const GraphNode& node) const
    {
        // assert we're in bounds to see if coordinate is in bounds
        assert(node.coordinate.first >= 0 && node.coordinate.first < _gridSize.first &&
            node.coordinate.second >= 0 && node.coordinate.second < _gridSize.second);

        // return the heuristic
        return _cachedHeuristicData[node.coordinate.first][node.coordinate.second];
    }
}