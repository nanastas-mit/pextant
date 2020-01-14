# __BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The xGDS platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
# __END_LICENSE__
import traceback
import json
import os

from pextant.api import Pathfinder
from pextant.explorers import Astronaut
from pextant.lib.geoshapely import GeoPoint, GeoEnvelope, LAT_LONG
from pextant.EnvironmentalModel import loadElevationMap

class SettingsTest:
    def __init__(self, root):
        self.DATA_ROOT = root
settings = SettingsTest(os.path.join('..','..','data','maps'))

def getCornersForMap(extent, zone, zoneLetter):
    if extent:
        nw_corner = GeoPoint(LAT_LONG, extent[3], extent[0])
        se_corner = GeoPoint(LAT_LONG, extent[1], extent[2])
        return nw_corner, se_corner
    return None, None


def getMap(site, maxSlope=15, extent=None):
    site_frame = site['name']
    dem_name = site_frame.replace(' ', '_') + '.tif'
    fullPath = os.path.join(settings.DATA_ROOT, 'dem', dem_name)
    if os.path.isfile(fullPath):
        zone = site['alternateCrs']['properties']['zone']
        zoneLetter = site['alternateCrs']['properties']['zoneLetter']

        if extent:
            nw_corner, se_corner = getCornersForMap(extent, zone, zoneLetter)
        else:
            nw_corner = None
            se_corner = None
        nw_corner_pad, se_corner_pad = GeoEnvelope(nw_corner, se_corner).addMargin(0.5, 30).getBounds()
        dem = loadElevationMap(fullPath, maxSlope=maxSlope, nw_corner=nw_corner_pad, se_corner=se_corner_pad)
        return dem
    return None


def testJsonSegments(plan):
    prevStation = None

    for index, entry in enumerate(plan.jsonPlan.sequence):
        if entry['type'] == 'Station':
            prevStation = entry['geometry']['coordinates']
        elif entry['type'] == 'Segment':
            nextStation = plan.jsonPlan.sequence[index + 1]['geometry']['coordinates']
            allCoords = [prevStation, nextStation]
            entry['geometry'] = {"coordinates": allCoords,
                                 "type": "LineString"}
            prevStation = nextStation
    return plan


def clearSegmentGeometry(plan):
    for elt in plan.jsonPlan.sequence:
        if elt.type == 'Segment':
            try:
                del elt['geometry']
            except:
                pass
            try:
                derivedInfo = elt['derivedInfo']
                del derivedInfo['distanceList']
                del derivedInfo['energyList']
                del derivedInfo['timeList']
                del derivedInfo['totalDistance']
                del derivedInfo['totalEnergy']
                del derivedInfo['totalTime']
            except:
                pass
    plan.save()
    return plan


def callPextant(request, plan, optimize=None, maxSlope=15, extent=None):
    executions = plan.executions
    if not executions:
        msg = 'Plan %s not scheduled; could not call Sextant' % plan.name
        raise Exception(msg)

    if not executions[0].ev:
        msg = 'No EV associated with plan %s; could not call Sextant' % plan.name
        raise Exception(msg)

    # Per Kevin, BASALTExplorer is not the thing.  Astronaut is the thing
    #     explorer = BASALTExplorer(executions[0].ev.mass)
    explorer = Astronaut(executions[0].ev.mass)

    site = plan.jsonPlan.site

    dem = getMap(site, maxSlope, extent)
    if not dem:
        raise Exception('Could not load DEM while calling Pextant for ' + site['name'])
    #
    pathFinder = Pathfinder(explorer, dem)
    sequence = plan.jsonPlan.sequence
    jsonSequence = json.dumps(sequence)
    try:
        #         print 'about to call pathfinder'
        if not optimize:
            optimize = str(plan.jsonPlan.optimization)
        else:
            plan.jsonPlan.optimization = optimize
        result = pathFinder.completeSearchFromJSON(optimize, jsonSequence)
        #         print 'actually came back from pathfinder'
        if 'NaN' not in result and 'Infinity' not in result:
            plan.jsonPlan.sequence = json.loads(result)
            plan.save()
    except Exception as e:
        traceback.print_exc()
        raise e
        pass

    return plan


