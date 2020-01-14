from astar import aStarSearch
from astarSEXTANT import astronautCost, MeshSearchElement

from pextant.EnvironmentalModel import GDALMesh
from pextant.explorers import Astronaut
from pextant.analysis.loadWaypoints import loadPoints


def runpextant(socketlink=None):
    hi_low = GDALMesh('maps/HI_lowqual_DEM.tif')
    waypoints = loadPoints('waypoints/HI_13Nov16_MD7_A.json')
    env_model = hi_low.loadSubSection(waypoints.geoEnvelope())
    env_model.setSocketLink(socketlink)
    astronaut = Astronaut(80)
    cost_function = astronautCost(astronaut, env_model, "Energy")
    start_node = MeshSearchElement(env_model.getMeshElement(waypoints[0]))
    end_node = MeshSearchElement(env_model.getMeshElement(waypoints[1]))
    out = aStarSearch(start_node, end_node, cost_function)
    print('done running pextant')
    print(out[1])
    return out[0]

if __name__ == '__main__':
    runpextant()