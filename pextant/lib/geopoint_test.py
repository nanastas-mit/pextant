from .geoshapely import *
import json
import pandas as pd
pd.options.display.max_rows = 5

latlong = LatLon()
origin = GeoPoint(latlong, 43.461621,-113.572019)
origincopy = GeoPolygon(latlong, [43.461621, 43.461622, 43.461622],[-113.572019,-113.572010, -113.572010])

with open('waypoints/MD10_EVA10_Stn18_Stn23_X.json') as data_file:
    data = json.load(data_file)
ways_and_segments = data['sequence']
s = pd.DataFrame(ways_and_segments)
waypoints = s[s['type']=='Station']['geometry']
w = waypoints.values.tolist()
latlongFull = pd.DataFrame(w)
latlongInter = latlongFull['coordinates'].values.tolist()
waypointslatlong = pd.DataFrame(latlongInter, columns=['longitude','latitude'])

print(waypointslatlong['latitude'].values, waypointslatlong['longitude'].values)
waypoints = GeoPolygon(latlong, waypointslatlong['latitude'].values, waypointslatlong['longitude'].values)
from EnvironmentalModel import *
info = loadElevationsLite("maps/hwmidres.tif")
nw_corner = GeoPoint(UTM(info["zone"]), info["nw_easting"], info["nw_northing"])
print(nw_corner)
XY = Cartesian(nw_corner, info["resolution"])
se_corner = GeoPoint(XY, info["width"], info["height"])
print(se_corner)
corners = LineString([(p.x, p.y) for p in [nw_corner, se_corner]])

bounds = corners.envelope
print(bounds)
zoomarea = waypoints.envelope
print(zoomarea)
intersection = bounds.intersection(zoomarea)
print(intersection)