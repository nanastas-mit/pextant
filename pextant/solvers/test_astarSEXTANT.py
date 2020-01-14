from .astarMesh import ExplorerCost
from pextant.EnvironmentalModel import GDALMesh
from pextant.mesh.triangularmesh import TriPolyMesh
from pextant.explorers import Astronaut
from pextant.settings import AMES_DEM
from pextant.mesh.MeshVisualizer import TriExpandViz
from pextant.solvers.astar import aStarSearch
from pextant.lib.geoshapely import GeoPoint, LAT_LONG
from pextant.solvers.astarMesh import MeshSearchElement

ames_em = TriPolyMesh(AMES_DEM).loadSubSection()
a = Astronaut(80)
costfunction = ExplorerCost(a, ames_em, 'Energy')
node = ames_em._getMeshElement(2767)
neighbours = ames_em._getNeighbours(2767)

#costfunction.setEndNode(node)
#costs = costfunction.calculateCostBetween(node,neighbours)
#cost1 = costfunction.getHeuristicCost(neighbours.__getitem__(0))
#print cost1
start_point = GeoPoint(ames_em.ROW_COL, 150, 100)
end_point = GeoPoint(ames_em.ROW_COL, 40, 120)
triviz = TriExpandViz(ames_em, start_point, end_point,100)
start = MeshSearchElement(ames_em.getMeshElement(start_point))
end = MeshSearchElement(ames_em.getMeshElement(end_point))
solution_path, expanded_items = aStarSearch(start, end, costfunction, triviz)
