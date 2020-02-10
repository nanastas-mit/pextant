import numpy as np
import networkx as nx
import pextant_cpp
from .SEXTANTsolver import sextantSearch, SEXTANTSolver, sextantSearchList
from .astar import aStarSearchNode, aStarNodeCollection, aStarCostFunction, aStarSearch
from pextant.EnvironmentalModel import EnvironmentalModel, GridMeshModel
from pextant.lib.geoshapely import GeoPoint, GeoPolygon, LONG_LAT
from pextant.solvers.nxastar import GG, astar_path
from time import time

class MeshSearchElement(aStarSearchNode):
    def __init__(self, mesh_element, parent=None, cost_from_parent=0):
        self.mesh_element = mesh_element
        self.derived = {} #the point of this is to store in memory expensive calculations we might need later
        super(MeshSearchElement, self).__init__(mesh_element.mesh_coordinate, parent, cost_from_parent)

    def goalTest(self, goal):
        return self.mesh_element.mesh_coordinate == goal.mesh_element.mesh_coordinate
        #return self.mesh_element.distanceToElt(goal.mesh_element) < self.mesh_element.parentMesh.resolution*3

    def getChildren(self):
        return MeshSearchCollection(self.mesh_element.getNeighbours(), self)

    def __getattr__(self, item):
        try:
            return MeshSearchElement.__getattribute__(self, item)
        except AttributeError:
            return getattr(self.mesh_element, item)

    def __str__(self):
        return str(self.mesh_element)

class MeshSearchCollection(aStarNodeCollection):
    def __init__(self, collection, parent=None):
        super(MeshSearchCollection, self).__init__(collection)
        self.derived = None
        self.parent = parent

    def __getitem__(self, index):
        mesh_search_element = MeshSearchElement(self.collection.__getitem__(index), self.parent)
        mesh_search_element.derived = dict(list(zip(['pathlength','time','energy'],self.derived[:,index])))
        return mesh_search_element

class ExplorerCost(aStarCostFunction):
    def __init__(self, astronaut, environment, optimize_on, cached=False, heuristic_accelerate=1):
        """

        :type astronaut: Astronaut
        :param environment:
        :type environment: GridMeshModel
        :param optimize_on:
        """
        super(ExplorerCost, self).__init__()
        self.explorer = astronaut
        self.map = environment
        self.optimize_vector = astronaut.optimizevector(optimize_on)
        self.heuristic_accelerate = heuristic_accelerate
        self.cache = cached
        if cached:
            self.cached["costs"] = self.cache_costs()

    def cache_all(self):
        end_y, end_x = self.end_node.y, self.end_node.x
        self.cached["costs"] = self.cache_costs()
        self.cached["heuristics"] = self.cache_heuristic((end_x, end_y))

    def cache_costs(self):
        kernel = self.map.searchKernel
        offsets = kernel.getKernel()
        dem = self.map

        dr = np.apply_along_axis(np.linalg.norm, 1, offsets) * self.map.resolution
        z = self.map.dataset_unmasked
        g = self.map.getGravity()
        neighbour_size = len(self.map.searchKernel.getKernel())
        slopes_rad = np.empty((dem.shape[0], dem.shape[1], neighbour_size))
        energy_cost = np.empty((dem.shape[0], dem.shape[1], neighbour_size))
        time_cost = np.empty((dem.shape[0], dem.shape[1], neighbour_size))
        path_cost = np.empty((dem.shape[0], dem.shape[1], neighbour_size))

        for idx, offset in enumerate(offsets):
            dri = dr[idx]
            slopes_rad[:, :, idx] = np.arctan2(np.roll(np.roll(z, -offset[0], axis=0), -offset[1], axis=1) - z, dri)
            energy_cost[:, :, idx], v = self.explorer.energy_expenditure(dri, slopes_rad[:, :, idx], g)
            time_cost[:,:,idx] = dri/v
            path_cost[:,:,idx] = dri/np.cos(slopes_rad[:, :, idx])*np.ones_like(z)

        return {'time': time_cost, 'path': path_cost, 'energy': energy_cost}

    def cache_heuristic(self, goal):
        g_x, g_y = goal
        r = self.map.resolution
        y, x = r*np.mgrid[0:self.map.y_size, 0:self.map.x_size]
        delta_y, delta_x = np.abs(y - g_y), np.abs(x - g_x)
        h_diagonal = np.minimum(delta_y, delta_x)
        h_straight = delta_y + delta_x

        # Patel 2010. See page 49 of Aaron's thesis
        manhattan_distance = (np.sqrt(2)-2) * h_diagonal + h_straight
        # Could also use euclidean distance
        # euclidean_distance = np.sqrt(delta_y ** 2 + delta_x ** 2)

        # Adding the energy weight
        explorer = self.explorer
        m = explorer.mass
        planet = self.map.planet

        energy_weight = explorer.minenergy[planet](m) #to minimize
        max_velocity = explorer.maxvelocity # to minimize

        optimize_weights = self.optimize_vector
        optimize_values = np.array([
            1, # Distance per m
            max_velocity, # time per m
            energy_weight # energy per m
        ])
        optimize_cost = manhattan_distance * np.dot(optimize_values, optimize_weights)
        #print(self.heuristic_accelerate)
        heuristic_cost = self.heuristic_accelerate * optimize_cost

        return heuristic_cost

    def get_cache_heuristic(self, start_row, start_col):
        return self.cached["heuristics"][start_row, start_col]

    def getHeuristicCost(self, elt):
        node = elt.mesh_element
        start_row, start_col = node.mesh_coordinate
        heuristic_fx = self.get_cache_heuristic if self.cache else self._getHeuristicCost
        return heuristic_fx(start_row, start_col)

    def getHeuristicCostRaw(self, rowcol):
        start_row, start_col = rowcol
        heuristic_fx = self.get_cache_heuristic if self.cache else self._getHeuristicCost
        return heuristic_fx(start_row, start_col)

    def _getHeuristicCost(self, start_row, start_col):
        r = self.map.resolution
        start_x, start_y = r*start_col, r*start_row
        end_x, end_y = self.end_node.x, self.end_node.y
        optimize_vector = self.optimize_vector

        # max number of diagonal steps that can be taken
        h_diagonal = min(abs(start_y - end_y), abs(start_x - end_x))
        h_straight = abs(start_y - end_y) + abs(start_x - end_x)  # Manhattan distance

        # Adding the energy weight
        m = self.explorer.mass
        # Aaron's thesis page 50
        if self.map.planet == 'Earth':
            energy_weight = 1.504 * m + 53.298
        elif self.map.planet == 'Moon' and self.explorer.type == 'Astronaut':
            energy_weight = 2.295 * m + 52.936
        elif self.map.planet == 'Moon' and self.explorer.type == 'Rover':
            p_e = self.explorer.P_e  # this only exists for rovers
            energy_weight = (0.216 * m + p_e / 4.167)
        else:
            # This should not happen
            raise TypeError("planet/explorer conflict, current planet: ", self.map.planet, "current explorer: ",
                            self.explorer.type)

        max_velocity = 1.6  # the maximum velocity is 1.6 from Marquez 2008
        d = np.array([1, max_velocity, energy_weight])
        d = np.dot(d, optimize_vector)

        # Patel 2010. See page 49 of Aaron's thesis
        heuristic_weight = self.heuristic_accelerate
        heuristic_cost = heuristic_weight*(d * np.sqrt(2) * h_diagonal + d * (h_straight - 2 * h_diagonal))
        # This is just Euclidean distance
        #heuristic_cost = d * np.sqrt((start_row - end_row) ** 2 + (start_col - end_col) ** 2)
        return heuristic_cost

    def getCostBetween(self, fromnode, tonodes):
        """:type fromnode: MeshSearchElement"""
        from_elt = fromnode.mesh_element
        to_cllt = tonodes.collection
        if self.cache:
            row, col = from_elt.mesh_coordinate
            selection = self.map.cached_neighbours[row,col]
            costs = self.cached["costs"]
            optimize_vector = np.array([
                costs['path'][row, col][selection],
                costs['time'][row, col][selection],
                costs['energy'][row, col][selection]
            ])
        else:
            optimize_vector = self.calculateCostBetween(from_elt, to_cllt)

        optimize_weights = self.optimize_vector
        costs = np.dot(optimize_vector.transpose(), optimize_weights)
        tonodes.derived = optimize_vector

        return list(zip(tonodes, to_cllt.get_states(), costs))

    def getCostToNeighbours(self, from_node):
        row, col = from_node.state
        neighbours = self.map.cached_neighbours(from_node.state)
        return self.cached[row, col, neighbours]

    def calculateCostBetween(self, from_elt, to_elts):
        """
            Given the start and end states, returns the cost of travelling between them.
            Allows for states which are not adjacent to each other.

            optimize_vector is a list or tuple of length 3, representing the weights of
            Distance, Time, and Energy
            Performance optimization: tonodes instead of tonode, potentially numpy optimized, only need to load info
            from fromnode once
        """
        explorer = self.explorer
        slopes, path_lengths = from_elt.slopeTo(to_elts)
        times = explorer.time(path_lengths, slopes)
        g = self.map.getGravity()
        energy_cost, _ = explorer.energy_expenditure(path_lengths, slopes, g)
        #TODO: rewrite this so not all functions need to get evaluated(expensive)
        optimize_vector = np.array([
            path_lengths,
            times,
            energy_cost
        ])
        return optimize_vector


class astarSolver(SEXTANTSolver):

    # algorithm type 'enum' rather than bool (previously: inhouse=true/false)
    PY_INHOUSE = 1
    PY_NETWORKX = 2
    CPP_NETWORKX = 3

    def __init__(self, env_model, explorer_model, viz=None, optimize_on='Energy',
                 cached=False, algorithm_type=PY_INHOUSE, heuristic_accelerate=1):
        self.explorer_model = explorer_model
        self.optimize_on = optimize_on
        self.cache = env_model.cached
        self.algorithm_type = algorithm_type
        self.G = None
        cost_function = ExplorerCost(explorer_model, env_model, optimize_on, env_model.cached, heuristic_accelerate)
        super(astarSolver, self).__init__(env_model, cost_function, viz)

        # if using networkx-based implementation, set G
        if algorithm_type == astarSolver.PY_NETWORKX or \
                algorithm_type == astarSolver.CPP_NETWORKX:
            self.G = GG(self)

    def accelerate(self, weight=10):
        self.cost_function = ExplorerCost(self.explorer_model, self.env_model, self.optimize_on,
                                          self.cache, heuristic_accelerate=weight)

    def get_solve_function(self):
        if self.algorithm_type == astarSolver.CPP_NETWORKX:
            solver = self.solvenx_cpp
        elif self.algorithm_type == astarSolver.PY_NETWORKX:
            solver = self.solvenx
        else:  # self.algorithm_type == astarSolver.PY_INHOUSE
            solver = self.solveinhouse
        return solver

    def solve(self, startpoint, endpoint):
        solver = self.get_solve_function()
        solver(startpoint, endpoint)

    def solveinhouse(self, startpoint, endpoint):
        env_model = self.env_model
        if env_model.elt_hasdata(startpoint) and env_model.elt_hasdata(endpoint):
            node1, node2 = MeshSearchElement(env_model.getMeshElement(startpoint)), \
                           MeshSearchElement(env_model.getMeshElement(endpoint))
            solution_path, expanded_items = aStarSearch(node1, node2, self.cost_function, self.viz)
            raw, nodes = solution_path
            if len(raw) == 0:
                coordinates = []
            else:
                coordinates = GeoPolygon(env_model.ROW_COL, *np.array(raw).transpose())
            search = sextantSearch(raw, nodes, coordinates, expanded_items)
            self.searches.append(search)
            return search
        else:
            return False

    def solvenx(self, startpoint, endpoint):
        env_model = self.env_model
        cost_function = self.cost_function
        start = env_model.getMeshElement(startpoint).mesh_coordinate
        target = env_model.getMeshElement(endpoint).mesh_coordinate
        if env_model.elt_hasdata(startpoint) and env_model.elt_hasdata(endpoint):
            if self.G == None:
                self.G = GG(self)
            self.cost_function.setEndNode(MeshSearchElement(env_model.getMeshElement(endpoint)))
            try:
                raw = astar_path(self.G, start, target, lambda a, b: self.cost_function._getHeuristicCost(*a))
                coordinates = GeoPolygon(self.env_model.COL_ROW, *np.array(raw).transpose()[::-1])
                search = sextantSearch(raw, [], coordinates, [])
                self.searches.append(search)
                return search
            except nx.NetworkXNoPath:
                return False
        else:
            return False

    def solvenx_cpp(self, startpoint, endpoint, c1=None, c2=None, c3=None):

        # get source and target coordinates
        source = self.env_model.getMeshElement(startpoint).mesh_coordinate
        target = self.env_model.getMeshElement(endpoint).mesh_coordinate

        # check that we have data at both start and end
        if self.env_model.elt_hasdata(startpoint) and self.env_model.elt_hasdata(endpoint):

            # prepare cost function
            self.cost_function.setEndNode(MeshSearchElement(self.env_model.getMeshElement(endpoint)))

            # perform search
            if c1 and c2 and c3:
                raw = pextant_cpp.astar_solve_with_callback(
                    source, target,
                    lambda a: 0.0,  # self.cost_function._getHeuristicCost(*a),
                    self.G.n,
                    c1, c2, c3
                )
            else:
                raw = pextant_cpp.astar_solve(
                    source, target,
                    lambda a: self.cost_function._getHeuristicCost(*a),
                    self.G.n
                )

            # if we have a good result
            if len(raw) > 0:

                # append result to 'searches' list and return
                coordinates = GeoPolygon(self.env_model.COL_ROW, *np.array(raw).transpose()[::-1])
                search = sextantSearch(raw, [], coordinates, [])
                self.searches.append(search)
                return search

        # default to fail result
        return False

    def weight(self, a, b):
        selection = (np.array(a) + self.env_model.searchKernel.getKernel()).tolist().index(list(b))
        costs = self.cost_function.cached["costs"]
        optimize_weights = self.cost_function.optimize_vector
        optimize_vector = np.array([
            costs['path'][a][selection],
            costs['time'][a][selection],
            costs['energy'][a][selection]
        ])
        costs = np.dot(optimize_vector.transpose(), optimize_weights)
        return costs

def generateGraph(em, weightfx):
    t1 = time()
    G = nx.DiGraph()
    rows, cols = list(range(em.y_size)), list(range(em.x_size))
    G.add_nodes_from((i, j) for i in rows for j in cols)
    for i in rows:
        dt = time() - t1
        #if dt > 60:
            #print(i)
        #if i%10 == 0:
        #    print(i)
        for j in cols:
            n = np.array((i,j))+em.searchKernel.getKernel()[em.cached_neighbours[i,j]]
            G.add_weighted_edges_from(((i,j), tuple(k), weightfx((i,j),tuple(k))) for k in n)
    t2 = time()
    print((t2-t1))
    return G

if __name__ == '__main__':
    from pextant.settings import WP_HI, HI_DEM_LOWQUAL_PATH
    from pextant.EnvironmentalModel import GDALMesh
    from pextant.explorers import Astronaut
    from pextant.mesh.MeshVisualizer import ExpandViz, MeshVizM

    jloader = WP_HI[7]
    waypoints = jloader.get_waypoints()
    envelope = waypoints.geoEnvelope()#.addMargin(0.5, 30)
    env_model = GDALMesh(HI_DEM_LOWQUAL_PATH).loadSubSection(envelope, maxSlope=35)
    astronaut = Astronaut(80)

    solver = astarSolver(env_model, astronaut, ExpandViz(env_model, 10000))
    segmentsout, rawpoints, items = solver.solvemultipoint(waypoints)
    jsonout = jloader.add_search_sol(segmentsout, True)

    matviz = MeshVizM()
    solgrid = np.zeros((env_model.y_size, env_model.x_size))
    for i in rawpoints:
        solgrid[i] = 1
    matviz.viz(solgrid)
