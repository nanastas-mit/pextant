import requests
import json
import sys
sys.path.append('../')
from pextant.analysis.loadWaypoints import JSONloader
WP_HI = JSONloader.from_file('../data/waypoints/HI_13Nov16_MD7_A.json')

xp_json = {"sequence": WP_HI.sequence}

config1 = 'https://localhost/pextant'
config2 = 'http://localhost:5000'
config = config1

send_json1 = {
    'param': {},
    'xp_json': xp_json
}

r1 = requests.post(config + '/setwaypoints',
                   data = json.dumps(send_json1), verify=False, timeout=5)
print((r1.json()))
send_json2 = {
        'return':'segmented'
}
r2 = requests.post(config+'/solve',
                   data = json.dumps(send_json2), verify=False,)
json_response = r2.json()
print(json_response)