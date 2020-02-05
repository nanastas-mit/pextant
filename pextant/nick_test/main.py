import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from pextant.EnvironmentalModel import load_legacy
from pextant.explorers import Astronaut, TraversePath
from pextant.lib.geoshapely import GeoPoint, GeoPolygon
from pextant.solvers.astarMesh import astarSolver
from pextant.viz.utils import hillshade
import time

# create the model
apollo14_grid_mesh = load_legacy("../notebooks/Documentation/Apollo14.txt")
apollo14_model = apollo14_grid_mesh.loadSubSection(maxSlope=10, cached=True)

# create the agent
agent = Astronaut(80)

# define star and endpoints
start = GeoPoint(apollo14_model.ROW_COL, 750, 100)
goal = GeoPoint(apollo14_model.ROW_COL, 650, 900)
waypoints = GeoPolygon([start, goal])

# create the solvers
pathfinder_x_cpp = astarSolver(apollo14_model, agent, algorithm_type=astarSolver.AlgorithmType.CPP_NETWORKX)
pathfinder_x = astarSolver(apollo14_model, agent, algorithm_type=astarSolver.AlgorithmType.PY_NETWORKX)

# find the optimal path
start = time.time()

# TODO: split out set waypoints and solve, allow for cacheing of heuristicsHan
out, _, _ = pathfinder_x_cpp.solvemultipoint(waypoints)
end = time.time()
elapsed_x_cpp = end - start
print("pathfinder_x_cpp time = {0:.3f}".format(elapsed_x_cpp))

# draw the path
hillshade(apollo14_model, 1)
plt.imshow(apollo14_model.obstacle_mask(), alpha=0.5, cmap='bwr_r')
plt.plot(*waypoints.to(apollo14_model.COL_ROW), linestyle='None', marker='*', markeredgecolor="k", markersize=15)
plt.plot(*out.coordinates().to(apollo14_model.COL_ROW))
red_patch = mpatches.Patch(color='red', alpha=0.5, label='Obstacle map')
plt.legend(handles=[red_patch])
plt.show()

'''
# analyze the path (energy/cost)
traverse = TraversePath.frommap(out.coordinates(), apollo14_model)
_, _, dr = agent.path_dl_slopes(traverse)
energies, v = agent.path_energy_expenditure(traverse)
cumsum_distance = np.cumsum(dr)
total_distance = cumsum_distance[-1]
cumsum_energy = np.cumsum(energies)/1000.
total_energy = cumsum_energy[-1]
plt.plot(cumsum_distance, cumsum_energy)
plt.xlabel('distance [m]')
plt.ylabel('energy [kJ]')
plt.title('Cumulative energy for EVA')
plt.show()
'''