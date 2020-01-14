from pextant.EnvironmentalModel import *
from pextant.explorers import Astronaut
from pextant.analysis.loadWaypoints import loadPoints
from pextant.api_future import *

filename = 'waypoints/HI_sextant_testing2_B.json'
with open(filename) as data_file:
    data = json.load(data_file)
jsonInput = json.dumps(data)

waypoints = loadPoints(filename)
dem_path = 'maps/HI_lowqual_DEM.tif'
dataset, info = loadElevationsLite(dem_path)
XY = Cartesian(info["nw_geo_point"], info["resolution"])
nw_corner = waypoints.geoEnvelope().addMargin(XY,10).upper_left
se_corner = waypoints.geoEnvelope().addMargin(XY,10).lower_right
EM2 = loadElevationMap(dem_path, maxSlope=15, planet='Earth', nw_corner=nw_corner, se_corner=se_corner,
                          desired_res=info["resolution"], no_val=-10000)

astronaut = Astronaut(45)
P = Pathfinder(astronaut, EM2)

aps =[]
for waypoint in waypoints.to(LAT_LONG).transpose():
    lat, lon = waypoint
    aps.append(ActivityPoint(GeoPoint(LAT_LONG,lat,lon), 0))

out = P.aStarCompletePath([0,0,1], aps, 'JSON')
print(out)