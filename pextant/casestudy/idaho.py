from pextant.api_future import *
from pextant.EnvironmentalModel import *
from osgeo import gdal

dem_path = 'maps/hwmidlow.tif'

import pandas as pd
import json
pd.options.display.max_rows = 5

with open('waypoints/MD10_EVA10_Stn18_Stn23_X.json') as data_file:
    data = json.load(data_file)
ways_and_segments = data['sequence']
s = pd.DataFrame(ways_and_segments)
waypoints = s[s['type']=='Station']['geometry']
w = waypoints.values.tolist()
latlongFull = pd.DataFrame(w)
latlongInter = latlongFull['coordinates'].values.tolist()
latlong = pd.DataFrame(latlongInter, columns=['longitude','latitude'])

latlongcoord = LatLongCoord(latlong['latitude'].values,latlong['longitude'].values)

utm = latLongToUTM(latlongcoord)
utmmaxx, utmminx = utm.easting.max(), utm.easting.min()
utmmaxy, utmminy = utm.northing.max(), utm.northing.min()

NWCorner = UTMCoord(utmminx, utmmaxy, utm.zone)
SECorner = UTMCoord(utmmaxx, utmminy, utm.zone)
print((UTMToLatLong(NWCorner)))
print((UTMToLatLong(SECorner)))

dem_map = loadElevationMap(dem_path, maxSlope=25, nw_corner=NWCorner, se_corner=SECorner)

astronaut = Astronaut(70)
P = Pathfinder(astronaut, dem_map)

lat,lon = latlong[['latitude','longitude']].iloc[7]
print((lat,lon))
latlong0 = LatLongCoord(lat, lon);
utm0 = latLongToUTM(latlong0)
ap0 = ActivityPoint(latlong0, 0)
row0, col0 = dem_map.convertToRowCol(utm0)
print((row0,col0))

lat,lon = latlong[['latitude','longitude']].iloc[8]
print((lat,lon))
latlong1 = LatLongCoord(lat, lon);
utm1 = latLongToUTM(latlong1)
ap1 = ActivityPoint(latlong1, 0)
row1, col1 = dem_map.convertToRowCol(utm1)
print((row1,col1))

lat,lon = latlong[['latitude','longitude']].iloc[9]
latlong2 = LatLongCoord(lat, lon);
utm2 = latLongToUTM(latlong2)
ap2 = ActivityPoint(latlong2, 0)
print((lat,lon))
ap2 = ActivityPoint(LatLongCoord(lat, lon), 0)
row2, col2 = dem_map.convertToRowCol(utm2)
print((row2,col2))

from bokeh.plotting import figure, output_file, show
from bokeh.io import hplot
output_file("lines.html", title="line plot example")

dh, dw = dem_map.elevations.shape
print(dw,dh)
# create a new plot with a title and axis labels
s1 = figure(title="simple line example", x_axis_label='x', y_axis_label='y', x_range=[0, 250], y_range=[250, 500])
s2 = figure(title="simple line example", x_axis_label='x', y_axis_label='y', x_range=[0, 250], y_range=[250, 500])

# add a line renderer with legend and line thickness
s1.image(image=[dem_map.elevations[::-1,:]], dw=dw, dh=dh, palette="Spectral11")
s2.image(image=[dem_map.obstacles[::-1,:]], dw=dw, dh=dh)
# show the results

final = P.aStarCompletePath([0, 0, 1], [ap1, ap2], 'tuple', [s1, s2], dh)

if len(final)>0:
    for elt in final[0]:
        s1.circle(elt[1], dh - elt[0], fill_color="yellow", line_color="yellow")
        s2.circle(elt[1], dh-elt[0], fill_color="yellow", line_color="yellow")
s1.circle([col1, col2], [dh - row1, dh - row2], fill_color="orange", line_color="orange")
s2.circle([col1, col2], [dh - row1, dh - row2], fill_color="orange", line_color="orange")

print(final)

p = hplot(s1, s2)
show(p)