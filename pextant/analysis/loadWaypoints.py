import json

import pandas as pd
from copy import deepcopy
from pextant.lib.geoshapely import *
import re
import os

def loadPointsOld(filename):
    parsed_json = json.loads(jsonInput)
    waypoints = []

    for element in parsed_json:  # identify all of the waypoints
        if element["type"] == "Station":
            lon, lat = element["geometry"]["coordinates"]
            time_cost = element["userDuration"]
            waypoints.append(GeoPolygon(LAT_LONG, lon, lat))

    return waypoints, parsed_json

class JSONloader:
    def __init__(self, sequence, filename=None):
        self.extension = '_plan.json'
        self.filename = None
        self.sequence = sequence

    @classmethod
    def from_file(cls, filepath):
        filename = os.path.basename(filepath).split('.')[0]
        dirname = os.path.dirname(filepath)
        fullfilename = os.path.join(dirname, filename)
        with open(filepath) as data_file:
            jsondata = json.load(data_file)
            return cls(jsondata['sequence'], fullfilename)

    def get_waypoints(self):
        #print('HI')
        #print(self.sequence)
        #print('Hi again')
        ways_and_segments = self.sequence
        s = pd.DataFrame(ways_and_segments)
        waypoints = s[s['type'] == 'Station']['geometry']
        w = waypoints.values.tolist()
        latlongFull = pd.DataFrame(w)
        latlongInter = latlongFull['coordinates'].values.tolist()
        waypointslatlong = pd.DataFrame(latlongInter, columns=['longitude', 'latitude'])
        return GeoPolygon(LAT_LONG, waypointslatlong['latitude'].values, waypointslatlong['longitude'].values)

    def get_segments(self):
        ways_and_segments = self.sequence
        s = pd.DataFrame(ways_and_segments)
        waypoints = s[s['type'] == 'Segment']['geometry']
        w = waypoints.values.tolist()
        latlongFull = pd.DataFrame(w)
        latlongInter = latlongFull['coordinates'].values.tolist()
        waypointslatlong = np.array(latlongInter[0])
        return GeoPolygon(LAT_LONG, waypointslatlong[:, 1], waypointslatlong[:, 0])

    def add_search_sol(self, segments, write_to_file=False):
        ways_and_segments = deepcopy(self.sequence)
        segment_iter = iter(segments)
        for i, element in enumerate(ways_and_segments):
            if element["type"] == "Segment":
                segment = segment_iter.next().tojson()
                ways_and_segments[i]["derivedInfo"].update(segment["derivedInfo"]) #merges our new info
                ways_and_segments[i]["geometry"] = segment["geometry"]
        raw_json = json.dumps(ways_and_segments)
        formatted_json = json.dumps(ways_and_segments, indent=4, sort_keys=True)
        if write_to_file and self.filename:
            new_filename = self.filename + self.extension
            with open(new_filename, 'w') as outfile:
                outfile.write(formatted_json)

        return raw_json


if __name__ == '__main__':
    test =json.dumps([{u'commands': [], u'uuid': u'ccf34b91-86f4-47ee-b03d-3dbbba6ba167',
      u'geometry': {u'type': u'Point', u'coordinates': [-155.20191861222781, 19.366498026755977]}, u'tolerance': 0.6,
      u'userDuration': 0, u'boundary': 0.6, u'type': u'Station', u'id': u'HIL11_A_WAY0'}, {
         u'derivedInfo': {u'durationSeconds': 28, u'straightLineDurationSeconds': 28,
                          u'distanceMeters': 25.15366493675656}, u'commands': [], u'type': u'Segment',
         u'id': u'HIL11_A_SEG1', u'uuid': u'69aa6e5f-6a10-4568-bfea-5bfbc8417ba7'},
     {u'commands': [], u'uuid': u'1a159ed9-77ee-4f79-9163-e3685a01a00c',
      u'geometry': {u'type': u'Point', u'coordinates': [-155.2016858384008, 19.36644374514718]}, u'tolerance': 0.6,
      u'userDuration': 0, u'boundary': 0.6, u'type': u'Station', u'id': u'HIL11_A_WAY1'}])

    jloader = JSONloader(test)
    jloader.get_waypoints()