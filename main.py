import requests
import json
from datetime import datetime, timedelta
from sys import argv

# Get user from argv
load_user = str(argv[1])

url = ("https://api.streamelements.com/kappa/v2/points/592b0d5610b3f73ce98ace4c/{}".format(load_user))
headers = {"Accept": "application/json"}
response = requests.request("GET", url, headers=headers)

# Forward response.text to json
j = json.loads(response.text)

# Convert the value from ['watchtime'] to human readable date (D:H:M)
getwatchtime = timedelta(minutes=j['watchtime'])                 
getdays = getwatchtime.days
gethours = getwatchtime.seconds // 3600
getminutes = (getwatchtime.seconds // 60) % 60
realtime = ("{} days {} hours {} minutes".format(getdays, gethours, getminutes))


print("Username: {} \nPoints: {} \nATH: {} \nWatchtime: {} \nRank: {}".format(
            j['username'],
            j['points'],
            realtime,
            j['pointsAlltime'],
            j['rank'])
        )

