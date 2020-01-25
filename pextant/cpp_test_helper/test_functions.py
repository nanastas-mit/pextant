'''
This file is for creating a simple 'test module' whose functions can be used for testing functionality
and performance of the pextant_cpp extension module.
'''

cpp_test_grid = [[".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                 [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                 [".", ".", "X", "X", "X", ".", ".", "X", "X", "."],
                 [".", ".", "X", "X", "X", ".", "X", "X", "X", "."],
                 [".", ".", "X", "X", "X", ".", "X", ".", ".", "."],
                 [".", ".", ".", ".", "X", ".", "X", "T", ".", "."],
                 [".", ".", ".", ".", "X", ".", "X", "X", ".", "."],
                 [".", ".", "X", ".", ".", ".", ".", ".", ".", "."],
                 [".", ".", "X", ".", ".", ".", ".", ".", ".", "."],
                 [".", ".", "X", ".", ".", ".", ".", ".", ".", "."]]

CPP_TEST_GRID_SIZE = 10
CPP_TEST_BLOCK_SYMBOL = "X"

cpp_test_oct_grid_neighbor_offsets = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)

cpp_test_sqrt_2 = 2 ** 0.5

def find_target() -> tuple:

    for row in range(len(cpp_test_grid)):
        for col in range(len(cpp_test_grid[0])):
            if cpp_test_grid[row][col] == "T":
                return col, row

    return -1, -1

def test_cost_function(u: tuple, v:tuple) -> float:

    euclidean_sum = 0
    for u_element, v_element in zip(u, v):
        euclidean_sum += (u_element - v_element) ** 2

    return euclidean_sum ** 0.5

def test_heuristic_manhattan(u: tuple) -> float:

    v = find_target()
    manhattan_sum = 0
    for u_element, v_element in zip(u, v):
        manhattan_sum += abs(u_element - v_element)

    return manhattan_sum

def test_heuristic_euclidean(u: tuple) -> float:

    v = find_target()
    return test_cost_function(u, v)

def test_heuristic_octgrid(u: tuple) -> float:

    v = find_target()

    x_diff = abs(u[0] - v[0])
    y_diff = abs(u[1] - v[1])
    min_diff = min(x_diff, y_diff)
    remaining = max(x_diff, y_diff) - min_diff

    return min_diff * cpp_test_sqrt_2 + remaining

def test_get_neighbors_and_cost(u: tuple) -> list:

    u_x = u[0]
    u_y = u[1]

    neighbors = []
    for neighbor_offset in cpp_test_oct_grid_neighbor_offsets:
        neighbor_x = neighbor_offset[0] + u_x
        neighbor_y = neighbor_offset[1] + u_y

        if 0 <= neighbor_x < CPP_TEST_GRID_SIZE and 0 <= neighbor_y < CPP_TEST_GRID_SIZE:
            if cpp_test_grid[neighbor_y][neighbor_x] != CPP_TEST_BLOCK_SYMBOL:

                neighbor = (neighbor_x, neighbor_y)
                neighbor_cost = test_cost_function(u, neighbor)
                neighbors.append((neighbor, neighbor_cost))

    return neighbors
