import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from pextant.EnvironmentalModel import load_legacy
from pextant.explorers import Astronaut
from pextant.lib.geoshapely import GeoPoint, GeoPolygon
from pextant.solvers.astarMesh import astarSolver
from pextant.viz.utils import hillshade
import time
import os

print("__name__ = {0}, __file__ = {1}, dirname = {2}".format(__name__, __file__, os.path.dirname(__file__)))

apollo14_grid_mesh = load_legacy("Apollo14.txt")
apollo14_model = apollo14_grid_mesh.loadSubSection(maxSlope=10, cached=True)

start = GeoPoint(apollo14_model.ROW_COL, 750, 100)
goal = GeoPoint(apollo14_model.ROW_COL, 650, 900)
waypoints = GeoPolygon([start, goal])

hillshade(apollo14_model, 1)
plt.imshow(apollo14_model.obstacle_mask(), alpha=0.5, cmap='bwr_r')
plt.plot(*waypoints.to(apollo14_model.COL_ROW), linestyle='None', marker='*', markeredgecolor="k", markersize=15)
red_patch = mpatches.Patch(color='red', alpha=0.5, label='Obstacle map')
plt.legend(handles=[red_patch])
plt.show()

agent = Astronaut(80)
pathfinder_x = astarSolver(apollo14_model, agent, inhouse=False)
pathfinder_in_house = astarSolver(apollo14_model, agent, inhouse=True)

start = time.time()
out, _, _ = pathfinder_x.solvemultipoint(waypoints)
end = time.time()
elapsed_x = end - start

start = time.time()
out, _, _ = pathfinder_in_house.solvemultipoint(waypoints)
end = time.time()
elapsed_in_house = end - start

nick = 1
nick -= 1

