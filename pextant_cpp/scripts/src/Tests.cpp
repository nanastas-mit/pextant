#include <iostream>
#include <queue>
#include <pybind11/pybind11.h>
#include "headers/GraphNode.h"
#include "headers/Tests.h"
#include "headers/Utils.h"

namespace py = pybind11;

namespace pextant
{
    void TestRandoms()
    {
        printf("\n===============\nTestRandoms BEGIN\n");

        const int numGenCount = 32;
        const int maxInt = 50;
        const int minInt = 30;
        const float maxFloat = 10.f;
        const float minFloat = -10.f;

        // ints
        printf("  GENERATING RANDOM INTS (%d, %d):\n", minInt, maxInt);
        for (int i = 0; i < numGenCount; ++i)
        {
            int generated = RandBetweenI(minInt, maxInt);
            printf("    %d: %d\n", i, generated);
        }

        // floats
        printf("\n  GENERATING RANDOM INTS (%f, %f):\n", minFloat, maxFloat);
        for (int i = 0; i < numGenCount; ++i)
        {
            float generated = RandBetweenF(minFloat, maxFloat);
            printf("    %d: %f\n", i, generated);
        }
        printf("\nTestRandoms END\n--------\n");
    }

    void TestPriorityQueue()
    {
        printf("\n===============\nTestPriorityQueue BEGIN\n");

        std::priority_queue<GraphNode, std::vector<GraphNode>, GraphNode::PriorityQueueSortFunction> q;

        // create some nodes
        const int testNodeCount = 10;
        GraphNode testNodes[testNodeCount];

        // initialize the nodes with random values, add them to q
        printf("  PUSHING %d NODES\n", testNodeCount);
        for (int i = 0; i < testNodeCount; ++i)
        {
            GraphNode& node = testNodes[i];
            int node_x = RandBetweenI(-20, 20);
            int node_y = RandBetweenI(-20, 20);
            node.coordinate = std::make_pair(node_x, node_y);
            node.gCost = RandBetweenF(0.f, 100.f);
            node.hCost = RandBetweenF(0.f, 100.f);
            printf(
                "    %d: Pushing node with <%d, %d, %f, %f>\n",
                i, node.coordinate.first, node.coordinate.second, node.gCost, node.hCost);

            q.push(testNodes[i]);
        }

        // pop nodes, printing out the order
        printf("  POPPING %d NODES\n", testNodeCount);
        while (!q.empty())
        {
            GraphNode node = q.top();
            q.pop();

            printf(
                "    %f: Popping node with <%d, %d, %f, %f>\n",
                node.GetFCost(), node.coordinate.first, node.coordinate.second, node.gCost, node.hCost);
        }

        printf("\nTestPriorityQueue END\n--------\n");
    }

    void TestPyList()
    {
        printf("\n===============\nTestPyFunctionCall BEGIN\n");
     
        py::list testList = py::list();

        const int numElements = 20;
        for (int i = 0; i < numElements; ++i)
        {
            int numToAdd = RandBetweenI(0, 11);
            testList.append(py::cast(numToAdd));
        }
        auto length = py::len(testList);
        auto size = testList.size();
        printf("  testList (length = %d):\n    < ", static_cast<int>(length));
        for (auto element : testList)
        {
            printf("%d ", element.cast<int>());
        }
        printf(">\n");

        testList.attr("reverse")();
        printf("  testList reversed (length = %d):\n    < ", static_cast<int>(length));
        for (auto element : testList)
        {
            printf("%d ", element.cast<int>());
        }
        printf(">\n");

        printf("\nTestPyFunctionCall END\n--------\n");
    }

    py::list& TestAstarReturn()
    {
        printf("\n===============\nTestAstarReturn BEGIN\n");

        py::list* testListPtr = new py::list();

        const int numElements = 20;
        for (int i = 0; i < numElements; ++i)
        {
            int v1 = RandBetweenI(0, 11);
            int v2 = RandBetweenI(0, 11);
            auto tupleToAdd = py::make_tuple(v1, v2);
            testListPtr->append(tupleToAdd);
        }
        auto size = testListPtr->size();
        printf("  testList (length = %d):\n", static_cast<int>(size));
        for (auto element : *testListPtr)
        {
            py::print("   ", element);
        }

        printf("\nTestAstarReturn END\n--------\n");

        return *testListPtr;
    }

    void TestHeuristicFunctionPassing(int x, int y, py::function& heuristic)
    {
        printf("\n===============\nTestHeuristicFunctionPassing BEGIN\n");

        auto u = py::make_tuple(x, y);
        auto val = heuristic(u).cast<float>();
        printf("  heruistic val for (%d, %d): %f", x, y, val);

        printf("\nTestHeuristicFunctionPassing END\n--------\n");
    }

    void TestAstarArgs(
        py::tuple& source,
        py::tuple& target,
        py::function& heuristic_func,
        py::function& find_neighbors_func) {}
}