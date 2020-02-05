import json

import pandas as pd
from copy import deepcopy
from pextant.lib.geoshapely import *
import numpy as np
import re
import os
pd.options.display.max_rows = 5
from pathlib import Path

def loadPointsOld(filename):
    parsed_json = json.loads(filename)
    waypoints = []

    for element in parsed_json:  # identify all of the waypoints
        if element["type"] == "Station":
            lon, lat = element["geometry"]["coordinates"]
            time_cost = element["userDuration"]
            waypoints.append(GeoPolygon(LAT_LONG, lon, lat))

    return waypoints, parsed_json

def get_gps_data(filename):
    """
    Gets GPS time series gathered from a traversal
    :param filename: <String> csv file from GPS team in format |date|time|name|latitude|longitude|heading
    :return: <pandas DataFrame> time_stamp|latitude|longitude
    """
    delimiter = r"\s+" # some of the columns are separated by a space, others by tabs, use regex to include both
    header_row = 0     # the first row has all the header names
    df = pd.read_csv(filename, sep=delimiter, header=header_row)
    df['date_time'] = pd.to_datetime(df['epoch timestamp'], unit='s')
    time_lat_long = df[['date_time', 'latitude', 'longitude']]
    gp = GeoPolygon(LAT_LONG, *df[['latitude', 'longitude']].as_matrix().transpose())
    return gp

#TODO: Need to move this over to test file
#filename = '../../data/ev_tracks/20161104A_EV1.csv'
#time_lat_long = get_gps_data(filename)

def sextant_loader(filepath):
    with open(filepath) as data_file:
        jsondata = json.load(data_file)
        latlongInter = np.array(jsondata['geometry']['coordinates']).transpose()
        return GeoPolygon(LONG_LAT, *latlongInter)

#this really is a xpjson loader
class JSONloader:
    def __init__(self, sequence, raw, filename=None):
        self.extension = '_plan.json'
        if isinstance(filename, Path):
            filename = str(filename.absolute())
        self.filename = filename
        self.raw = raw
        self.sequence = sequence

    @classmethod
    def from_string(cls, str):
        return cls(json.loads(str))

    @classmethod
    def from_file(cls, filepath):
        if isinstance(filepath, Path):
            filepath = str(filepath.absolute())
        stem = os.path.basename(filepath).split('.')[0]
        parent = os.path.dirname(filepath)
        fullfilename = os.path.join(parent, stem)
        with open(filepath) as data_file:
            jsondata = json.load(data_file)
            return cls(jsondata['sequence'], jsondata, fullfilename)

    def get_waypoints(self):
        #print('HI')
        #print(self.sequence)
        #print('Hi again')
        ways_and_segments = self.sequence
        s = pd.DataFrame(ways_and_segments)
        waypoints = s[s['type'] == 'Station']['geometry']
        w = waypoints.values.tolist()
        latlongFull = pd.DataFrame(w)
        latlongInter = np.array(latlongFull['coordinates'].values.tolist()).transpose()
        return GeoPolygon(LONG_LAT, *latlongInter)

    def get_segments(self):
        ways_and_segments = self.sequence
        s = pd.DataFrame(ways_and_segments)
        waypoints = s[s['type'] == 'Segment']['geometry']
        w = waypoints.values.tolist()
        latlongFull = pd.DataFrame(w)
        latlongInter = latlongFull['coordinates'].values.tolist()
        waypointslatlong = []
        for elt in latlongInter:
            waypointslatlong.extend(elt)
        return GeoPolygon(LONG_LAT, *np.array(waypointslatlong).transpose())

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
            rawfile = self.raw
            rawfile["sequence"] = ways_and_segments
            new_filename = self.filename + self.extension
            with open(new_filename, 'w') as outfile:
                json.dump(rawfile, outfile, indent=4, sort_keys=True)

        return raw_json


if __name__ == '__main__':
    from pextant.settings import *
    md = JSONloader.from_file(MD_HI[6])
    sextantsol = md.get_segments()
    test =json.dumps([{'commands': [], 'uuid': 'ccf34b91-86f4-47ee-b03d-3dbbba6ba167',
      'geometry': {'type': 'Point', 'coordinates': [-155.20191861222781, 19.366498026755977]}, 'tolerance': 0.6,
      'userDuration': 0, 'boundary': 0.6, 'type': 'Station', 'id': 'HIL11_A_WAY0'}, {
         'derivedInfo': {'durationSeconds': 28, 'straightLineDurationSeconds': 28,
                          'distanceMeters': 25.15366493675656}, 'commands': [], 'type': 'Segment',
         'id': 'HIL11_A_SEG1', 'uuid': '69aa6e5f-6a10-4568-bfea-5bfbc8417ba7'},
     {'commands': [], 'uuid': '1a159ed9-77ee-4f79-9163-e3685a01a00c',
      'geometry': {'type': 'Point', 'coordinates': [-155.2016858384008, 19.36644374514718]}, 'tolerance': 0.6,
      'userDuration': 0, 'boundary': 0.6, 'type': 'Station', 'id': 'HIL11_A_WAY1'}])

    jloader = JSONloader(test)
    jloader.get_waypoints()