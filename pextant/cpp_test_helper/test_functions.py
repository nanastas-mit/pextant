'''
This file is for creating a simple 'test module' whose functions can be used for testing functionality
and performance of the pextant_cpp extension module.
'''

test_grid = [[".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
             [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
             ["X", ".", "X", "X", "X", ".", ".", "X", "X", "."],
             [".", ".", "X", "X", "X", ".", "X", "X", "X", "X"],
             [".", "X", "X", "X", "X", ".", "X", ".", ".", "."],
             [".", "X", ".", ".", "X", ".", "X", "T", ".", "."],
             [".", ".", ".", ".", "X", "X", "X", "X", ".", "."],
             [".", ".", "X", ".", ".", "X", ".", "X", ".", "."],
             [".", ".", "X", ".", ".", ".", ".", ".", ".", "."],
             [".", ".", "X", ".", ".", ".", ".", ".", ".", "."]]
NUM_TEST_GRID_ROWS = len(test_grid)
NUM_TEST_GRID_COLS = len(test_grid[0])

test_kernel = [
    [-1, -1],
    [-1, 0],
    [-1, 1],
    [0, -1],
    [0, 1],
    [1, -1],
    [1, 0],
    [1, 1],
]
KERNEL_SIZE = len(test_kernel)

BLOCK_SYMBOL = "X"
GOAL_SYMBOL = "T"
SQRT_2 = 2 ** 0.5


def find_target() -> tuple:

    for row in range(NUM_TEST_GRID_ROWS):
        for col in range(NUM_TEST_GRID_COLS):
            if test_grid[row][col] == GOAL_SYMBOL:
                return row, col

    return -1, -1

def test_cost_function(u: tuple, v:tuple) -> float:

    x_diff = abs(u[1] - v[1])
    y_diff = abs(u[0] - v[0])
    diag_steps = min(x_diff, y_diff)
    horizontal_steps = x_diff + y_diff

    return diag_steps * SQRT_2 + (horizontal_steps - 2 * diag_steps)

def test_heuristic_manhattan(u: tuple) -> float:

    v = find_target()
    manhattan_sum = 0
    for u_element, v_element in zip(u, v):
        manhattan_sum += abs(u_element - v_element)

    return manhattan_sum

def test_heuristic_euclidean(u: tuple) -> float:

    v = find_target()

    euclidean_sum = 0
    for u_element, v_element in zip(u, v):
        euclidean_sum += (u_element - v_element) ** 2

    return euclidean_sum ** 0.5

def test_heuristic_octgrid(u: tuple) -> float:

    v = find_target()
    return test_cost_function(u, v)

def test_get_neighbors_and_cost(u: tuple) -> list:

    neighbors = []
    for neighbor_offset in test_kernel:

        neighbor = (neighbor_offset[0] + u[0], neighbor_offset[1] + u[1])
        if is_node_inbounds_and_valid(neighbor):

            neighbor_cost = test_cost_function(u, neighbor)
            neighbors.append((neighbor, neighbor_cost))

    return neighbors

def is_node_inbounds_and_valid(u: tuple) -> bool:

    u_row = u[0]
    u_col = u[1]

    if 0 <= u_row < NUM_TEST_GRID_ROWS and 0 <= u_col < NUM_TEST_GRID_COLS:
        if test_grid[u_row][u_col] != BLOCK_SYMBOL:
            return True

    return False

def create_costs_map() -> list:

    cost_map = []
    for row in range(0, NUM_TEST_GRID_ROWS):

        cost_row = []
        for col in range(0, NUM_TEST_GRID_COLS):

            cost_list = []
            for iKernel in range(0, KERNEL_SIZE):

                offset = test_kernel[iKernel]
                neighbor = (offset[0] + row, offset[1] + col)

                if is_node_inbounds_and_valid(neighbor):
                    neighbor_cost = test_cost_function((row, col), neighbor)
                else:
                    neighbor_cost = -1.0

                cost_list.append(neighbor_cost)

            cost_row.append(cost_list)

        cost_map.append(cost_row)

    return cost_map

def create_obstacle_map() -> list:

    obstacle_map = []
    for row in range(0, NUM_TEST_GRID_ROWS):

        obstacle_row = []
        for col in range(0, NUM_TEST_GRID_COLS):

            obstacle_value = 0
            if test_grid[row][col] == BLOCK_SYMBOL:
                obstacle_value = 1

            obstacle_row.append(obstacle_value)

        obstacle_map.append(obstacle_row)

    return obstacle_map

def create_heuristic_map() -> list:

    h_map = []
    for row in range(0, NUM_TEST_GRID_ROWS):

        h_row = []
        for col in range(0, NUM_TEST_GRID_COLS):

            u = (row, col)
            h_cost = test_heuristic_octgrid(u)
            h_row.append(h_cost)

        h_map.append(h_row)

    return h_map
