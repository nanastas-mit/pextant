from pextant.settings import explorer, DEM_AMES
from .astarMesh import astarSolver, MeshSearchElement

env_model = DEM_AMES[50].loadSubSection()

solver = astarSolver(env_model, explorer)
h = solver.cost_function.create_heuristic_cache((50, 50))
solver.cost_function.setEndNode(MeshSearchElement(env_model.getMeshElement((100,100))))
cost = solver.cost_function.getHeuristicCost(MeshSearchElement(env_model.getMeshElement((10,10))))

print(cost)