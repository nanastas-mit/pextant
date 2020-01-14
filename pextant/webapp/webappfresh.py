from flask import Flask, session
from flask_socketio import SocketIO
import sys
sys.path.append('../../')
from .serialgps import GPSSerialThread, serial_ports, GPSSerialEmulator, RandomThread, FakeEmitter
from pextant.lib.geoshapely import LAT_LONG, GeoPoint, Cartesian, UTM
from pextant.analysis.loadWaypoints import JSONloader
from pathlib2 import Path
from DateTime import DateTime

import json
from threading import Thread

app = Flask(__name__)
app.secret_key = "any random string"
socketio = SocketIO(app)

def printmessage(message):
    print(message)

class SocketChannel:

    def __init__(self, socket, channelname, onrecieve=printmessage):
        self.channelname = channelname
        self.socket = socket
        self.onrecieve = self.socket.on(channelname)(lambda data: onrecieve(json.loads(data)))

    def emit(self, message):
        print(self.channelname + ' emitting: ' + str(message))
        self.socket.emit(self.channelname, message)

thread = Thread()
def gps_on(data):
    global thread
    print('got gps request')
    print(data)
    if data["command"] == "start":
        if not thread.isAlive():
            print('starting gps')
            session["gps_channel"].emit('testing')
            thread = GPSSerialThread(session["gps_channel"], FakeEmitter(), data["data"])
            thread.record = True
            thread.start()
        else:
            print('gps already on')
    elif data["command"] == "stop" and thread != None:
        thread.stop()
        thread = None
    elif data["command"] == "hist":
        data = '../../data/gps/hawaii17/gps_raw_1510357679.3.json'
        with open(data, 'r') as f:
            jsondata = json.load(f)
        times = [DateTime(elt["time"]).ISO8601() for elt in jsondata]
        obj = {}
        obj["coords"] = [jsondata]
        obj["times"] = [times]
        session["gps_channel"].emit(json.dumps(obj))



def connected_devices(data):
    print('connected devices request')
    session["connected_devices"].emit(json.dumps(serial_ports()))

PLAN_DIR = Path('../../data/waypoints')
def plan_manager(data):
    if data["command"] == "listdir":
        file = [x.name for x in PLAN_DIR.iterdir() if x.is_file()]
        session["plan_manager"].emit(json.dumps(file))

    if data["command"] == "readfile":
        session["plan_manager"].emit(json.load(data["data"]))

    if data["command"] == "writefile":
        filename = data["data"]["filename"]
        xpjson = data["data"]["xpjson"]
        json.dump(xpjson, PLAN_DIR / filename)

@socketio.on('connect')
def handle_new_connection():
    session["status_channel"] = SocketChannel(socketio, 'status')
    session["connected_devices"] = SocketChannel(socketio, 'connected_devices', connected_devices)
    session["gps_channel"]  = SocketChannel(socketio, 'gps', gps_on)
    session["plan_manager"] = SocketChannel(socketio, 'planner', plan_manager)
    session["status_channel"].emit('Server echoing')
    print('Client connected')


#meshmessenger = SocketChannel(socketio, 'meshmsg')

@socketio.on('calibrate')
def getcalibration(data):
    print('got calibration request')
    global thread
    global GPS_OFFSET
    mappoint = json.loads(data)
    print(data)
    gpspoint = json.loads(thread.most_recent_gps_point_raw)
    print(gpspoint)
    geomappoint = GeoPoint(LAT_LONG, mappoint["latitude"], mappoint["longitude"])
    geogpspoint = GeoPoint(LAT_LONG, gpspoint["latitude"], gpspoint["longitude"])
    print(geogpspoint)
    print(geomappoint)
    offset = geogpspoint.to(UTM(5)) - geomappoint.to(UTM(5))
    print(offset)
    GPS_OFFSET = {
        'easting': offset[0],
        'northing': offset[1]
    }
    thread.gpsoffset = GPS_OFFSET
    socketio.emit('message', 'calibration completed')
    socketio.emit('message', json.dumps(GPS_OFFSET))

@socketio.on('pextant')
def getpextant(data):
    print('got pextant request')
    global thread
    global meshmessenger
    waypoint = None
    #if data != "":
    #waypoint0 = json.loads(thread.most_recent_gps_point)
    #waypoint1 = json.loads(data)
    #print waypoint1['latitude']
    #print waypoint0['latitude']
    #waypoint =  json.dumps({"latitude":[waypoint0['latitude'], waypoint1['latitude']],
    #             "longitude": [waypoint0['longitude'], waypoint1['longitude']]})
    #print waypoint
        #waypoints = runpextant(meshmessenger)
    #else:

        #waypoints = runpextant(meshmessenger)


    #print waypoints
    #waypointsdict = {
    #    'latitude': list(waypoint[0]),
    #    'longitude': list(waypoint[1])}

    #print waypointsdict
    #waypointsstr = json.dumps(waypointsdict)
    #print waypointsstr
    #socketio.emit('pextant', waypointsstr)

@socketio.on('disconnect')
def disconnect():
    global thread
    if thread.isAlive():
        thread.stop()
    print('disconnected')

if __name__ == '__main__':
    socketio.run(app, host='localhost', port=2999)