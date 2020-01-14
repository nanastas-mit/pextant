from pextant.EnvironmentalModel import GDALMesh
from pextant.analysis.loadWaypoints import JSONloader
from pextant.api_future.pextantHarness import getCornersForMap, getMap, callPextant
from pextant.lib.geoshapely import GeoPolygon, LAT_LONG
from pextant.settings import AMES_DEM, TEST_JSON


def generateExtent(lat, long):
    extent = [int[0], lat[1], int[1], lat[0]]
    return extent

def generate_site(sitename):
    site = {
        'name': sitename,
        'alternateCrs': {
            'properties': {
                'zone': None,
                'zoneLetter': None
            }
        }
    }
    return site


def testGetCornersForMap():
    env_model = GDALMesh(AMES_DEM).loadSubSection()
    rows, cols = [2, 50], [2, 60]
    lat, int = GeoPolygon(env_model.ROW_COL, rows, cols).to(LAT_LONG)
    extent = generateExtent(lat, int)
    nw_corner, se_corner = getCornersForMap(extent, None, None)
    print((GeoPolygon([nw_corner, se_corner]).to(env_model.ROW_COL)))

def testGetMap():
    site = generate_site('Ames')
    env_model = GDALMesh(AMES_DEM).loadSubSection()
    rows, cols = [2,50],[2,60]
    lat, int = GeoPolygon(env_model.ROW_COL, rows, cols).to(LAT_LONG)
    extent = generateExtent(lat, int)
    dem = getMap(site, extent=extent)
    print([dem.width, dem.height])

class ExecutionTest:
    def __init__(self, ev):
        self.ev = ev
class EVTest:
    def __init__(self, mass):
        self.mass = mass
class JsonPlanTest:
    def __init__(self, map, jsonpath):
        self.jsonPlan = JSONloader.from_file(jsonpath)
        self.sequence = self.jsonPlan.sequence
        self.optimization = "Energy"
        self.site = generate_site(map)

class PlanTest:
    def __init__(self, map, jsonpath, mass):
        self.jsonPlan = JsonPlanTest(map, jsonpath)
        self.executions = [ExecutionTest(EVTest(mass))]

    def save(self):
        return None

def testCallPextant():
    plan = PlanTest('HI_lowqual_DEM',TEST_JSON,80)
    bound = JSONloader.from_file(TEST_JSON).get_waypoints().geoEnvelope()
    extent = generateExtent(*bound.to(LAT_LONG))
    callPextant(None, plan, extent=extent, maxSlope=35)

if __name__ == '__main__':
    testCallPextant()