#!/bin/env python3

import requests
import json
from datetime import datetime, timedelta
import sqlite3 as sl

# -- Todo --
# 
# : db class is a big mess.
# : Make it work for Windows users (not prior)
# : Change database rank from TEXT to INT so we can diff it without int() it
# : Lots of vars that is not needed
# : What if data_file is missing? Or the SQL table is not set?
# : realtime in convertminutes() should be colored in print, not have it stored in db
# O (statusCode check) Error check on request twitch_channels to avoid errors if 404 or if other err code is True
# O (Removed print_data completely) print_data need to be in a def?
# O (Removed Option. Only SQL now) Option of sql/request needed? Why not only use sqlite?
# 
# --------------
# -- Settings --
twitch_username = "mepparn"
twitch_channels = ["roshtein", "deuceace", "vondice"]
data_file = "/home/lemones/.twitch_points.data"
#
# -- Globals --
total_points = 0
# --------------
#

class load:

    def __init__(self, chname, luser):
        self.load_user = luser
        self.channel_name = chname

    def get_id(self, cname):
        # Get id from channel name and call self.get_data with id value
        # get values from get_data and insert or update sql database
        url = "https://api.streamelements.com/kappa/v2/channels/{}".format(cname)
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        j = json.loads(response.text)
        if 'statusCode' in j:
            print("Error: {}".format(j['message']))
            exit()

        self.channel_id = j['_id']
        self.channel_name = j['displayName']

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
        getwatchtime = timedelta(minutes=mins)
        getdays = getwatchtime.days
        gethours = getwatchtime.seconds // 3600
        getminutes = (getwatchtime.seconds // 60) % 60
        realtime = ("\t\033[1m{}\033[0m days \033[1m{}\033[0m hours \033[1m{}\033[0m minutes".format(getdays, gethours, getminutes))
        return realtime

    def init(self):
        self.get_id(self.channel_name)

        getdb = db(data_file)
        # Get db_old values to diff
        getdb.db_old(self.channel_name, self.points, self.rank)
        # Update DB before print because of diff
        getdb.db_update(self.channel_name, self.username, self.points, self.rank, self.realtime)
        # Done. Let's print
        getdb.db_print(self.channel_name)


class db:

    def __init__(self, master):
        self.connect()

    def connect(self):
        self.con = sl.connect(data_file)
        self.c = self.con.cursor()

    def disconnect(self):
        self.c.close()

    def db_old(self, channel_name, points, rank):
        with self.con:
            data = self.con.execute("SELECT points,rank FROM Channels where name=?", (channel_name,))
            for row in data:
                self.points_old = row[0]
                self.rank_old = row[1]
        self.disconnect()

    def db_update(self, channel_name, username, points, rank, watchtime):
        sql_script = """UPDATE Channels SET points=?, rank=?, watchtime=? WHERE name=?"""
        sql_update = [(points, rank, watchtime, channel_name)]
        with self.con:
            for row in self.con.execute("SELECT name FROM Channels WHERE name=?", (channel_name,)):
                self.con.executemany(sql_script, sql_update)
                break
            else:
                return
        self.disconnect()

    def db_print(self, channel_name):
        with self.con:
            data = self.con.execute("SELECT name,points,rank,watchtime FROM Channels WHERE name=?", (channel_name,))
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

# -- Start --
def main():
    for i in twitch_channels:
        start(i, twitch_username)

    print("\033[1mTotal:\033[0m {}".format(total_points))

def start(argu, argc):
    getdata = load(argu, argc)
    getdata.init()
# -----------


if __name__ == "__main__":
    main()
