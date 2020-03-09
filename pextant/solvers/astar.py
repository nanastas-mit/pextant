from heapq import heappop, heappush
from itertools import count
import warnings
from pextant.mesh.abstractcomponents import MeshCollection

class aStarSearchNode(object):
    def __init__(self, state, parent=None, cost_from_parent=0):
        self.state = state
        self.parent = parent
        self.cost_from_parent = cost_from_parent

    def goalTest(self, goal):
        return self.state == goal.state

    def getPath(self):
        node = self
        statepath = [node.state]
        nodepath = [node]
        while node.parent:
            statepath.append(node.parent.state)
            nodepath.append(node.parent)
            node = node.parent

        statepath.reverse()
        nodepath.reverse()
        return (statepath, nodepath)

    def getChildren(self):
        pass

class aStarNodeCollection(object):
    """
    class to be overwritten
    """
    def __init__(self, collection):
        '''
        :type collection: MeshCollection
        '''
        self.collection = collection

    def __getitem__(self, index):
        return aStarSearchNode(self.collection[index])

    #TODO: need to enforce this
    def get_states(self):
        return self.collection.get_states()

class aStarCostFunction(object):
    def __init__(self):
        self.end_node = None
        self.cache = False
        self.cached = {
            "costs": None,
            "heuristics": None
        }

    def setEndNode(self, end_state):
        elt = end_state.mesh_element
        if self.cache:
            self.cache_heuristic((elt.x, elt.y))
        self.end_node = elt

    def cache_heuristic(self, end_state):
        pass

    def getHeuristicCost(self, node):
        return 0

    def getCostBetween(self, fromnode, tonode):
        return 0

def aStarSearch(start_node, end_node, cost_function, viz=None):
    """
    returns the path (as a list of coordinates), followed by the number of
    states expanded, followed by the total cost

    this function will return a list of states between two waypoints
    to get the full path between all waypoints, we will basically just use
    this function multiple times with each set
    as long as the number of waypoints is reasonable we should be fine

    costFunction supports a vector costFunction, with the
    three vector elements representing: 'Energy', 'Time', or 'Distance'
    As of right now 'Energy' just refers to metabolic energy.
    """
    push = heappush
    pop = heappop
    if start_node.goalTest(end_node):
        return (start_node, 0, 0)

    cost_function.setEndNode(end_node) #this also caches all the heuristic costs if need be
    start_node.cost = 0
    # agenda contains pairs (cost, node)
    c = count()
    queue = [(0, next(c), start_node, 0)]
    current_node = start_node # needed in case of early exit of loop

    enqueued = {}
    explored = set()

    while queue:
        #print([(idx, mesh.mesh_coordinate) for idx, mesh in agenda])
        _, __, current_node, acc_cost = pop(queue)
        current_node_state = current_node.state
        if current_node.goalTest(end_node):
            return (current_node.getPath(), explored)

        if current_node_state in explored:
            continue

        explored.add(current_node_state)

        for child_node, child_state, cost in cost_function.getCostBetween(current_node, current_node.getChildren()):
            if child_state in explored: #and cost_to_node >= g_cost.get(child_node_state,0):
                continue
            ncost = acc_cost + cost
            if child_state in enqueued:
                qcost, h = enqueued[child_state]
                if qcost <= ncost:
                    continue
            else:
                h = cost_function.getHeuristicCostRaw(child_state)
                #print(current_node_state, child_node_state, ncost+h, ncost, h)
            enqueued[child_state] = ncost, h
            estimated_cost = ncost+h
            # this if statement is a shortcut that does a lot of things at the same time
            push(queue, (estimated_cost, next(c), child_node, ncost))
            if viz:
                viz.add(child_state, estimated_cost)
        if viz:
            viz.addcount()

    # if it can't find a solution
    warnings.warn('no solution found')
    #if viz:
    #    viz.draw()
    return (([],[]), explored)