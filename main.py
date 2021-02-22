import requests
import json
from datetime import datetime, timedelta
from sys import argv
import sqlite3 as sl

# Rosh: 592b0d5610b3f73ce98ace4c

class load:

    def __init__(self, master):
        self.load_user = "mepparn" #str(argv[1])
        self.sech = master

    def getid(self, cname):
        url = "https://api.streamelements.com/kappa/v2/channels/{}".format(cname)
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        j = json.loads(response.text)
        self.chid = j['_id']

    def channel(self, cid):
        url = ("https://api.streamelements.com/kappa/v2/points/{}/{}".format(cid, self.load_user))
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        j = json.loads(response.text)
        # Get realtime of watchtime (minutes) from self.convertminutes()
        realtime = self.convertminutes(j['watchtime'])

        print("Username: {} \nPoints: {} \nATH: {} \nWatchtime: {} \nRank: {}".format(
                    j['username'],
                    j['points'],
                    j['pointsAlltime'],
                    realtime,
                    j['rank'])
                )

    def convertminutes(self, mins):
        # Convert the value from ['watchtime'] to human readable date (D:H:M)
        getwatchtime = timedelta(minutes=mins)
        getdays = getwatchtime.days
        gethours = getwatchtime.seconds // 3600
        getminutes = (getwatchtime.seconds // 60) % 60
        realtime = ("{} days {} hours {} minutes".format(getdays, gethours, getminutes))
        return realtime

    def init(self):
        chid = self.getid(self.sech)
        self.channel(self.chid)



class db:

    def __init__(self, master):
        self.db_name = "data.db"

    def connect(self):
        con = sl.connect('data.db')
        c = con.cursor()

    def check_table(self):
        with con:
            con.execute("""
                CREATE TABLE CHANNEL (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    points INTEGER,
                    watchtime TEXT,
                    rank TEXT
                );
            """)

        sql = 'INSERT INTO CHANNEL (id, name, points, watchtime, rank) values(?, ?, ?, ?, ?)'
        data = [
            (3, 'ROSHTEIN', j['points'], realtime, j['rank'])
        ]

        with con:
            con.executemany(sql, data)

    def print_db(self):
        with con:
            data = con.execute("SELECT * FROM CHANNEL")
            for row in data:
                print(row)




getdata = load("roshtein")
getdata.init()
