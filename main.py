#!/bin/env python3

import sys
import json
from datetime import datetime, timedelta
import sqlite3 as sl
import requests

# -- Todo --
# : db class is a big mess.
# : Calls for other def's should not been made inside a def.
# : Make it work for Windows users (not prior)
# : Change database rank from TEXT to INT so we can diff it without int()'ing it?
# : Lots of vars that is not needed
# : What if data_file is missing? Or the SQL table is not set? A construct in db would be good.
# : realtime in convertminutes() should be colored in print, not have it stored in db
#   I have set up self.realtime_clean for future fix.
# O (statusCode check) Error check on request twitch_channels to avoid errors if 404 or if other err code is True
# O (Removed print_data completely) print_data need to be in a def?
# O (Removed Option. Only SQL now) Option of sql/request needed? Why not only use sqlite?
#
# --------------
# -- Settings --
twitch_username = "mepparn"
twitch_channels = ["roshtein", "deuceace", "vondice"]
data_file = "./data.db"
# --------------
# -- Globals --
total_points = 0
realtime_clean = 0

try:
    get_arg = sys.argv[1]
    twitch_username = get_arg
except IndexError:
    pass


class Load:

    def __init__(self, chname, luser):
        self.load_user = luser
        self.channel_name = chname
        self.realtime_clean = 0

    def get_id(self, cname):
        url = "https://api.streamelements.com/kappa/v2/channels/{}".format(cname)
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        j = json.loads(response.text)
        if 'statusCode' in j:
            print("Error: {}".format(j['message']))
            exit()

        self.channel_id = j['_id']
        self.channel_name = j['displayName']
        # Call get_data with channel _id
        self.get_data(self.channel_id)

    def get_data(self, cid):
        url = ("https://api.streamelements.com/kappa/v2/points/{}/{}".format(cid, self.load_user))
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        j = json.loads(response.text)
        if 'statusCode' in j:
            print("Error: {}".format(j['message']))
            exit()

        self.username = j['username']
        self.points = j['points']
        self.pointsAlltime = j['pointsAlltime']
        self.realtime = self.convertminutes(j['watchtime'])
        self.rank = j['rank']
        global total_points
        total_points += self.points

    def convertminutes(self, mins):
        # Convert the value from ['watchtime'] to human readable date (D:H:M)
        # Could have months also, but different days per month gives a less accurate total watchtime.
        getwatchtime = timedelta(minutes=mins)
        getdays = getwatchtime.days
        gethours = getwatchtime.seconds // 3600
        getminutes = (getwatchtime.seconds // 60) % 60
        self.realtime_clean = ("{} days {} hours {} minutes".format(getdays, gethours, getminutes))
        return "\t\033[1m{}\033[0m days \033[1m{}\033[0m hours \033[1m{}\033[0m minutes".format(getdays, gethours, getminutes)

    def init(self):
        self.get_id(self.channel_name)
        getdb = db(data_file)
        # Get db_old values to diff
        getdb.db_old(self.channel_name, self.points, self.rank, self.username)
        # Update DB before print because of diff
        getdb.db_update(self.channel_name, self.username, self.points, self.rank, self.realtime)
        # Done. Let's print
        getdb.db_print(self.channel_name)


class db:

    def __init__(self, master):
        self.connect()
        self.points_old = 0
        self.rank_old = 0

    def connect(self):
        self.con = sl.connect(data_file)
        self.c = self.con.cursor()

    def disconnect(self):
        self.c.close()

    def db_old(self, channel_name, points, rank, username):
        with self.con:
            data = self.con.execute("SELECT points,rank FROM Channels where name=? AND user=?", (channel_name, username))
            for row in data:
                self.points_old = row[0]
                self.rank_old = row[1]
        self.disconnect()

    def db_update(self, channel_name, username, points, rank, watchtime):
        sql_script = """UPDATE Channels SET points=?, rank=?, watchtime=?, name=?, user=? WHERE name=? AND user=?"""
        sql_update = [(points, rank, watchtime, channel_name, username, channel_name, username)]
        with self.con:
            for row in self.con.execute("SELECT name FROM Channels WHERE name=? AND user=?", (channel_name, username,)):
                self.con.executemany(sql_script, sql_update)
                break
            else:
                send_t = (channel_name, username, points, rank, watchtime)
                self.db_add(send_t)
                return
        self.disconnect()

    def db_add(self, this):
        sql_script = """INSERT OR REPLACE INTO Channels (name, user, points, rank, watchtime)
                        VALUES(?,?,?,?,?)"""
        self.con.execute(sql_script, this)


    def db_print(self, channel_name, username=twitch_username):
        with self.con:
            data = self.con.execute("SELECT name, points, rank, watchtime, user FROM Channels WHERE name=? AND user=?", (channel_name, username))
            for row in data:
                print("\033[1m\033[95m{}\033[0m\033[0m  \033[1mPoints:\033[0m {}{}\033[1m Rank:\033[0m {}{}\n{} \n".format(
                            row[0],
                            row[1], self.diff_this(row[1], self.points_old),
                            row[2], self.diff_this(row[2], self.rank_old),
                            row[3]))
        self.disconnect()

    def diff_this(self, of, to):
        diff = int(of) - int(to)
        diff_v = None

        if diff >= 0:
            if diff == 0:
                diff_v = ""
            else:
                diff_v = "\033[1m(\033[0m\033[92m+\033[0m{}\033[1m)\033[0m".format(abs(diff))
        else:
            diff_v = "\033[1m(\033[0m\033[91m-\033[0m{}\033[1m)\033[0m".format(abs(diff))
        return("{}".format(diff_v))


if __name__ == "__main__":
    for i in twitch_channels:
        getdata = Load(i, twitch_username)
        getdata.init()
    print("\033[1mTotal:\033[0m {}".format(total_points))
