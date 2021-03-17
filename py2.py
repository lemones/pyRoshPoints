#!/bin/env python3

import requests
import json
from datetime import datetime, timedelta
from sys import argv
import argparse
import sqlite3 as sl


# -- Todo --
# Change database rank from TEXT to INT so we can diff it easy
#
# --------------
# -- Settings --
twitch_username = "mepparn"
twitch_channels = ["roshtein", "deuceace", "vondice"]
data_file = "/home/lemones/.twitch_points.data"
print_data = "sql" # sql/request

total_points = 0
# --------------

class load:

    def __init__(self, chname, luser):
        self.load_user = luser
        self.channel_name = chname

        self.channel_id = 0
        self.username = None
        self.points = 0
        self.pointsAlltime = 0
        self.realtime = 0
        self.rank = 0

    def get_id(self, cname):
        # Get id from channel name and call self.get_data with id value
        # get values from get_data and insert or update sql database
        url = "https://api.streamelements.com/kappa/v2/channels/{}".format(cname)
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        j = json.loads(response.text)

        self.channel_id = j['_id']
        self.channel_name = j['displayName']

        self.get_data(self.channel_id)

    def get_data(self, cid):
        url = ("https://api.streamelements.com/kappa/v2/points/{}/{}".format(cid, self.load_user))
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers)
        j = json.loads(response.text)
        # Get realtime of watchtime (minutes) from self.convertminutes()
        realtime = self.convertminutes(j['watchtime'])

        self.username = j['username']
        self.points = j['points']
        self.pointsAlltime = j['pointsAlltime']
        self.realtime = realtime
        self.rank = j['rank']
        global total_points
        total_points += self.points

        if (self.print_data == "sql"):
            print("yes")
        elif (self.print_data == "request"):
            self.print_data()
        else:
            return

    def print_data(self):
            print("\033[1m\033[95m{}\033[0m\033[0m  \033[1mPoints:\033[0m {}\033[1m Rank:\033[0m {}\n{} \n".format(
                        self.channel_name,
                        #self.username,
                        self.points,
                        #self.pointsAlltime,
                        self.rank,
                        self.realtime)
                    )

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
        # Done. Let's print (diff code in db_print def)
        getdb.db_print(self.channel_name)


# DB
class db:

    def __init__(self, master):

        self.points_old = 0
        self.rank_old = 0

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

                # Check diff of points
                points_diff = row[1] - self.points_old
                if points_diff >= 0:
                    if points_diff == 0:
                        points_diff_v = ""
                    else:
                        points_diff_v = "+"
                else:
                    points_diff_v = "-"


                print("\033[1m\033[95m{}\033[0m\033[0m  \033[1mPoints:\033[0m {}({}{})\033[1m Rank:\033[0m {}\n{} \n".format(
                            row[0],
                            row[1], points_diff_v, points_diff,
                            row[2],
                            row[3])
                        )
        self.disconnect()


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
