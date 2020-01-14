import json
from threading import Thread, Event
from time import time

import eventlet
import numpy as np
import numpy.ma as ma
import pynmea2
import serial
from serial.tools import list_ports

from pextant.EnvironmentalModel import GDALMesh
from pextant.lib.geoshapely import GeoPoint, LAT_LONG, Cartesian, UTM, GeoEnvelope

eventlet.monkey_patch(thread=True)

def serial_ports():
    com_ports = []
    for connection in list_ports.comports():
        com_ports.append(connection.description)
    return com_ports


class StoppableThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

class GDALMeshServer(StoppableThread):
    def __init__(self, socket_channel):
        super(GDALMeshServer, self).__init__()
        self.object = None
        self.socket_channel = socket_channel
        socket_channel.setSender(self.processMessage)

    def processMessage(self, function, arguments):
        if function == 'load':
            self.object = GDALMesh(arguments)
        elif function == 'selectarea':
            self.object.loadSubSection(arguments[0], arguments[1])
        elif function == 'getinfo':
            self.object.jsonify()

class GPSRecorderThread(StoppableThread):
    def __init__(self, socket_channel, socket_channel2):
        super(GPSRecorderThread, self).__init__()
        self.socket_channel = socket_channel
        self.socket_channel2 = socket_channel2
        self.gpsoffset = {
            'easting': 0,
            'northing': 0
        }
        self.recorded_points = {}
        self.delay = 0.1
        self.record = True
        self.do_emit = True
        self.most_recent_gps_point = None
        self.most_recent_gps_point_raw = None
        self.save_name_baseline = str(time())
        #EM = GDALMesh('maps/HI_lowqual_DEM.tif').loadSubSection(
        #    GeoEnvelope(GeoPoint(LAT_LONG, 19.370299271704212, -155.2175380561995),
        #                GeoPoint(LAT_LONG, 19.359626542672096, -155.19608451884082)))
        #ma_el = ma.masked_array(EM.elevations, mask=EM.elevations < 0)
        #self.EM = EM
        #self.ma_el = ma_el
        #self.maxelevation = ma_el.max()
        #self.minelevation = ma_el.min()

    def getSaveName(self, extraname):
        return '../../data/gps/hawaii17/gps_' + extraname + '_' + self.save_name_baseline + '.json'

    def correctForOffset(self, lat, long):
        easting, northing = GeoPoint(LAT_LONG, lat, int).to(UTM(5))
        print(self.gpsoffset["easting"])
        print(self.gpsoffset['northing'])
        trueasting = easting - self.gpsoffset["easting"]
        truenorthing = northing - self.gpsoffset['northing']
        return GeoPoint(UTM(5), trueasting, truenorthing).to(LAT_LONG)

    def newGPSPoint(self, lat, lon, alt):
        print(lat, lon)
        raw_point_json = self.recordAndSaveGPSPoint(lat, lon, alt, 'raw')
        print((lat, lon, alt))
        #correctedPointLat, correctedPointLong = self.correctForOffset(lat, lon)
        #self.getMesh(correctedPointLat, correctedPointLong)
        #corrected_point_json = self.recordAndSaveGPSPoint(correctedPointLat, correctedPointLong, 0, 'corrected')
        #self.most_recent_gps_point = corrected_point_json
        self.most_recent_gps_point_raw = raw_point_json
        self.emit(raw_point_json) #would normally be corrected

    def getMesh(self, lat, lon):
        center = GeoPoint(LAT_LONG, lat, lon)
        upper_left, lower_right = GeoEnvelope(center, center).addMargin(self.EM.ROW_COL, 5).getBounds()
        ul_row, ul_col = upper_left.to(self.EM.ROW_COL)
        lr_row, lr_col = lower_right.to(self.EM.ROW_COL)
        local_elevations = self.ma_el[ul_row:lr_row, ul_col:lr_col]
        elevations_normalized = (local_elevations - self.minelevation)/(self.maxelevation-self.minelevation)
        np.ma.set_fill_value(elevations_normalized, 0)
        elevations_normalized_corrected  = elevations_normalized.filled()
        ul_lat, ul_lon = upper_left.to(LAT_LONG)
        ul_row, ul_col = upper_left.to(self.EM.ROW_COL)
        lr_lat, lr_lon = lower_right.to(LAT_LONG)
        lr_row, lr_col = lower_right.to(self.EM.ROW_COL)

        message = {
            'dem': elevations_normalized_corrected.tolist(),
            'upper_left': {
                'latitude': ul_lat,
                'longitude': ul_lon,
                'row': ul_row,
                'col': ul_col
            },
            'lower_right': {
                'latitude': lr_lat,
                'longitude': lr_lon,
                'row': lr_row,
                'col': lr_col
            }
        }
        json_local_elevations = json.dumps(message)
        print(json_local_elevations)
        print(self.socket_channel2.channelname)
        self.socket_channel2.emit(message)

    def recordAndSaveGPSPoint(self, lat, lon, alt, extraname=''):
        latlon_point = {
            'time': time(),
            'latitude': lat,
            'longitude': lon,
            'altitude': alt}
        if extraname in self.recorded_points:
            self.recorded_points[extraname].append(latlon_point)
        else:
            self.recorded_points[extraname] = [latlon_point]

        savefile_name = self.getSaveName(extraname)

        if self.record:
            with open(savefile_name, 'w') as outfile:
                json.dump(self.recorded_points[extraname], outfile)

        latlon_point_json = json.dumps(latlon_point)
        return latlon_point_json

    def emit(self, latlon_point_json):
        print(str(time()))
        if self.do_emit:
            self.socket_channel.emit(latlon_point_json)


class GPSSerialThread(GPSRecorderThread):
    def __init__(self, socket_channel, socket_channel2, comport):
        super(GPSSerialThread, self).__init__(socket_channel, socket_channel2)
        self.comport = comport
        self.baudrate = 4800
        self.serial_reference = None
        self.timer = time()
        self.connect_time = None
        self.connected = False

    def openSerialConnection(self):
        if self.comport in ''.join(serial_ports()):
            self.connected = True
            if self.connect_time == None:
                self.connect_time = time()
            if self.serial_reference == None and time()-self.connect_time>1:
                ser = serial.Serial()
                ser.port = self.comport
                ser.baudrate = self.baudrate
                ser.timeout = 1
                ser.open()
                self.serial_reference = ser
            return self.serial_reference != None
        else:
            self.connected = False
            if self.serial_reference is not None:
                self.connect_time = None
                self.serial_reference.close()
                self.serial_reference = None
            return False

    def streamFromSerial(self):
        while not self.stopped():
            if self.openSerialConnection():
                data = self.serial_reference.readline()
                if data[0:6] == '$GPGGA':
                    msg = pynmea2.parse(data)
                    print (msg)
                    self.newGPSPoint(msg.latitude, msg.longitude, msg.altitude)
                    eventlet.sleep()

    def run(self):
        self.streamFromSerial()


class RandomThread(StoppableThread):
    def __init__(self, socket_ref):
        self.socket_ref = socket_ref
        self.delay = 1
        self.record = True
        super(RandomThread, self).__init__()

    def randomNumberGenerator(self):
        while not self.stopped():
            print('emitting')
            self.socket_ref.emit('event', str(time()))
            eventlet.sleep()

    def run(self):
        self.randomNumberGenerator()


class GPSSerialEmulator(GPSRecorderThread):
    def __init__(self, socket_channel, socket_channel2, comport):
        self.time = time()
        super(GPSSerialEmulator, self).__init__(socket_channel, socket_channel2)

    def randomPointGenerator(self):
        startime = time()
        while not self.stopped():
            newtime = time()
            deltat = newtime - self.time
            if deltat > 1:
                self.time = newtime
                center = GeoPoint(LAT_LONG, 19.401912952980723, -155.26565760546461)
                XY = Cartesian(center, 1)
                totaldelta = newtime - startime
                randomPointLat, randomPointLong = GeoPoint(XY, 0.5*totaldelta, 0.5*totaldelta).to(LAT_LONG)
                self.newGPSPoint(randomPointLat, randomPointLong, 0)
            #the sleeping is required if we are running this inside webappfresh
            eventlet.sleep()

    def run(self):
        self.randomPointGenerator()


class FakeEmitter(object):
    def __init__(self):
        pass

    def emit(self, message):
        print('emitting')
        print(message)

if __name__ == '__main__':
    print((json.dumps(serial_ports())))
    gps = GPSSerialEmulator(FakeEmitter(), FakeEmitter(),'COM10')
    gps.record = False
    gps.start()
