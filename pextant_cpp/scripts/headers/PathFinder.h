#ifndef PATH_FINDER
#define PATH_FINDER

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <queue>
#include <tuple>
#include "headers/GraphNode.h"

namespace pextant
{
    class PathFinder
    {
        //=====================================
        // TYPES
        //=====================================
    public:
        enum class Type
        {
            DIJKSTRA,
            ASTAR,
            DSTAR
        };

        //=====================================
        // FIELDS
        //=====================================
    public:
        // --- PROPERTIES ---
        Type getFinderType()
        {
            return _finderType;
        }
        bool getCached()
        {
            return _cached;
        }

    private:
        // --- VARS ---
        // type of this particular finder
        Type _finderType = Type::ASTAR;
        // whether or not data is currently cached
        bool _cached = false;

        // stores num_rows and num_cols of the graph
        std::pair<int, int> _gridSize = std::make_pair(0, 0);

        // an array of offsets that specifies which nodes are accessible (i.e. are neighbors of) a given node
        typedef std::vector<GraphCoordinate> Kernel;
        Kernel _kernel;

        // a num_rows x num_columns 'matrix' that stores 'cost to neighbors' and 'heuristic cost to goal' information
        typedef std::vector<std::vector<GraphNodeCachedDatum>> NodeDataMatrix;
        NodeDataMatrix _cachedNodeData;

        // PRIORITY QUEUE q:
        //   create queue for determining which nodes to process next.
        //   queue is sorted by f-value, smallest to largest.
        //   f-value is sum of the cost needed to get to node from source (known to be min at queue-add time)
        //     and expected 'heuristic' cost needed to get to target (a 'best guess')
        typedef std::priority_queue<GraphNode, std::vector<GraphNode>, GraphNode::PriorityQueueSortFunction> GraphNodeQueue;
        GraphNodeQueue _q;

        // MAP explored:
        //  create dictionary for tracking which nodes are in the closed set.
        //  key is node in closed set, value is that node's parent.
        typedef std::unordered_map<GraphCoordinate, GraphCoordinate, GraphNode::CoordinateHashFunction> ExploredMap;
        ExploredMap _explored;

        // MAP enqueued:
        //   keeps track of what nodes have ever been on the queue (i.e. looked at in any capacity).
        //   useful for cacheing hCost (never changes) and keeping track of min all-time gCost
        //     => only needed as part of an optimization (fewer priority queue inserts)
        typedef std::unordered_map<GraphCoordinate, std::pair<float, float>, GraphNode::CoordinateHashFunction> EnqueuedMap;
        EnqueuedMap _enqueued;

        //=====================================
        // METHODS
        //=====================================
    public:
        // constructors
        PathFinder() {}
        PathFinder(Type finderType_) : PathFinder()
        {
            _finderType = finderType_;
        }

        // solvers
        pybind11::list& AstarSolve(pybind11::tuple source, pybind11::tuple target);
        bool AstarStep(int steps) {
            return true;
        }
        void PrepareCache(
            pybind11::list& to_neighbor_costs,
            pybind11::list& obstacle_map,
            pybind11::list& to_goal_heuristics,
            pybind11::list& kernel);
        void ClearCache()
        {
            _kernel.swap(Kernel());
            _cachedNodeData.swap(NodeDataMatrix());
            _gridSize = std::make_pair(0, 0);
            _cached = false;
        }
        void ResetProgress()
        {
            _q.swap(GraphNodeQueue());
            _explored.swap(ExploredMap());
            _enqueued.swap(EnqueuedMap());
        }
        pybind11::list& GetAstarResult() {
            return *(new pybind11::list());
        }

    private:
        // gets the neighbor of {node} at the specified kernel index
        //   returns false if kernelIndex is invalid, if neighbor would be 'out of bounds', or if there neighbor is blocked by an obstacle
        //   returns true otherwise
        bool TryGetNeighborAtKernelIndex(
            const GraphNode& node, 
            int kernelIndex, 
            GraphNode& outNeighbor,
            float& outCost) const;

        // gets heuristic cost to goal for given node
        float GetNodeHeuristic(const GraphNode& node) const;

        // convers a coordinate to a py_tuple
        pybind11::tuple GraphCoordinateToPyTuple(const GraphCoordinate& coordinate)
        {
            return pybind11::make_tuple(coordinate.first, coordinate.second);
        }
    };
}

#endif // !PATH_FINDER
