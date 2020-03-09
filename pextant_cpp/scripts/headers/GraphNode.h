#ifndef GRAPH_NODE_HEADER
#define GRAPH_NODE_HEADER

#include <assert.h>
#include <pybind11/pybind11.h>
#include <stdexcept>
#include <tuple>

namespace pextant
{
    // first = row, second = column
    typedef std::pair<int, int> GraphCoordinate;

    class GraphNode
    {
    public:
        GraphCoordinate coordinate;
        GraphCoordinate parentCoordinate;
        float gCost;
        float hCost;

        // constructors
        GraphNode(const GraphCoordinate& coordinate_, float gCost_);
        GraphNode(const pybind11::tuple& pyCoordinate, float gCost_);
        GraphNode();

        // operator overloads
        inline bool operator==(const GraphNode& other) const { return coordinate == other.coordinate; }

        // methods
        inline float GetFCost() const
        {
            return this->gCost + this->hCost;
        }

        // classes
        class PriorityQueueSortFunction // used in priority_queue
        {
        public:
            bool operator () (const GraphNode& lhs, const GraphNode& rhs) const
            {
                return lhs.GetFCost() > rhs.GetFCost();
            }
        };
        class CoordinateHashFunction // used in unordered_map
        {
        public:
            size_t operator () (const GraphCoordinate& coordinate) const
            {
                auto a = (long)coordinate.first;
                auto b = (long)coordinate.second;

                // Szudzik's function for mapping two integers to one, uniquely
                size_t A = a >= 0 ? 2 * a : -2 * a - 1;
                size_t B = b >= 0 ? 2 * b : -2 * b - 1;
                long long C = (A >= B ? A * A + A + B : A + B * B) / 2;

                return a < 0 && b < 0 || a >= 0 && b >= 0 ? C : -C - 1;
            }
        };
    };
}
#endif // !GRAPH_NODE_HEADER