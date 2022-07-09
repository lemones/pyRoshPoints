#!/bin/python3

import sys
import json
import logging
from datetime import datetime, timedelta
import sqlite3 as sl
import requests

# Todo:
# - Save channel id to db and if exist don't request API to reduce calls.
# - Add 24h timer to compare points for the last 24h. Heavy stuff.
#   Will however make one extra SQL connection. Can I get id without that extra sql?
# - Instead of global var's, create a list or dict instead. (list is faster?)
# - db->db_points is called 6 times per channel request. No idea why?
# - No need to close the db at functions in db(). It will close when __del__ is called.
# - Better having error-handling in __main__ instead from in Get_data()
# - Can create json file for data instead of using sqlite.
# - Calls to function inside class would be better in __main__ instead from within the class

username = "mepparn"
channels = [ "roshtein", "deuceace", "vondice", "frankdimes" ]
data_file = "data.db"

# Globals (this is to messy)
channel_name = ""
points = 0
points_all_time = 0
watchtime = 0
rank = 0
total_points = 0

# If arg is set, use that instead of username
# !! Create a check so only valid chars is used, so the API does not thinks we abusing.
try:
    get_arg = sys.argv[1]
    username = get_arg
except IndexError:
    pass


class Get_data:

    def __init__(self, channel):
        self.channel = channel
        self.total_points = 0
        self.err_status = None
        self.get_channel_data() # Called from here or from __main__?
        if self.err_status == 1:
            # No need to remove it from list. It will still continue to next one
            #channels.remove(self.channel)
            pass
        else:
            getdb = db(channel)
            getdb.db_points()

    def get_channel_data(self):

        # Put data in globals so it can be called from outside.
        # Create an global list/dict would be better and less messy.
        global channel_name, points, points_all_time, \
            watchtime, rank, total_points

        headers = { "Accept": "application/json" }

        # Get channel id
        url_id = "https://api.streamelements.com/kappa/v2/channels/{}".format(self.channel)
        response = requests.request("GET", url_id, headers=headers)
        ans = json.loads(response.text)
        if 'statusCode' in ans:
            print("[{}] Error: {}".format(col('*', 'r'), ans['message']))
            exit()
        self.channel_id = ans['_id']
        self.channel_name = ans['displayName']

        # Get data from channel id
        url_data = "https://api.streamelements.com/kappa/v2/points/{}/{}".format(self.channel_id, username)
        response = requests.request("GET", url_data, headers=headers)
        ans = json.loads(response.text)
        if 'statusCode' in ans:
            print("[{}] {} ({})".format(col('*', 'r'), ans['message'], self.channel))
            # If user is not found remove channel from list and continue.
            #channels.remove(self.channel)
            self.err_status = 1
        else:
            # If no statusCode given, continue.
            self.err_status = None
            points = ans['points']
            points_all_time = ans['pointsAlltime']
            watchtime = self.convertminutes(ans['watchtime'])
            rank = ans['rank']
            channel_name = self.channel_name
            total_points += points
            getdb = db(self.channel)

    def convertminutes(self, mins):
        """ Convert minutes to human readable real time """
        getwatchtime = timedelta(minutes=mins)
        getdays = getwatchtime.days
        gethours = getwatchtime.seconds // 3600
        getminutes = (getwatchtime.seconds // 60) % 60
        self.realtime_clean = ("{} days {} hours {} minutes".format(getdays, gethours, getminutes))
        # Cleaner to read
        return f"{col(getdays, 'b')} days {col(gethours, 'b')} hours {col(getminutes, 'b')} minutes"
        #return "\033[1m{}\033[0m days \033[1m{}\033[0m hours \033[1m{}\033[0m minutes".format(getdays, gethours, getminutes)


class db:

    def __init__(self, channel):
        self.channel = channel
        self.points_old = 0 # Declared for new user with no data
        self.rank_old = 0   # Declared for new user with no data

        self.chan_name = None
        self.points = None
        self.rank = None
        self.watchtime = None
        self.user = None
        self.diff_points = None
        self.diff_rank = None

        self.connect()

    def connect(self):
        self.con = sl.connect(data_file)
        self.c = self.con.cursor()

    def disconnect(self):
        # This can be put in __del__ instead? Just one-liner.
        self.c.close()

    def db_points(self):
        """ Fetch data from db where name=channel_name & user=username """

        with self.con:
            # Do it with try: to intercept errors and print it out gracefully
            # There should be no errors tho...
            try:
                # Get data before updating new values (for diffs)
                sql = f"SELECT name, points, rank, watchtime, user \
                      FROM Channels WHERE name='{channel_name}' AND user='{username}'"
                data = self.con.execute(sql)
                for row in data:
                    # Set values and call print_data() for output
                    self.chan_name = row[0]
                    self.points = row[1]
                    self.rank = row[2]
                    self.watchtime = row[3]
                    self.user = row[4]
                    self.diff_points = self.diff_this(points, row[1])
                    self.diff_rank = self.diff_this(rank, row[2])
                    self.print_data()
                    break
                else:
                    # If no data of user, call db_new to create it
                    # db_new will then recall db_points
                    # This can be infinte if db_new errors. Fix an error counter?
                    print(f"[{col('*', 'y')}] No data of {username} found. Adding new.")
                    self.db_new()
            except Exception:
                print(f"[{col('*', 'r')}] Exception error in db_points")

        self.disconnect()
        self.db_update()

    def db_update(self):
        """ Update the data where user=username & channel=channel_name """
        with self.con:
            try:
                sql = f"""UPDATE Channels SET points='{points}', rank='{rank}', watchtime='{watchtime}' WHERE user='{username}' AND name='{channel_name}'"""
                self.con.execute(sql)
            except Exception:
                print(f"[{col('*', 'r')}] Exception error in db_update")
        self.disconnect()

    def db_new(self):
        """ Adding new data to the sqlite db """
        with self.con:
            # Maybe better to just INSERT? This will not be called if already exists anyway.
            # Also, just REPLACE is an alias of INSERT OR REPLACE, so can be shorten down
            sql = f"""INSERT OR REPLACE INTO Channels ( points,rank,watchtime,name,user )
                    VALUES ( '{points}', '{rank}', '{watchtime}', '{channel_name}', '{username}' )"""
            self.con.execute(sql)
        self.disconnect()
        # New data created, jump back to db_points to print it
        # This makes a second call to the database, this can be avoided. Fix!
        self.db_points()

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

    def print_data(self):
        """ Print the collected data """

        # This is so uggly...
        print("{} {} {} {}{} {} {}{} {} {}\n   {}{}\n".format(
            col(self.chan_name, 'y'),
            col("", 'b'),
            col('Points:', 'b'),
            self.points,
            self.diff_points,
            col('Rank:', 'b'),
            self.rank,
            self.diff_rank,
            col("ATH:", 'b'),
            points_all_time,
            len(self.chan_name)*" ",
            self.watchtime
        ))


    def __del__(self):
        self.disconnect()


def col(text, value):
    """ For colored output """
    # b - bold-foreground
    # y - bold-yellow (should be yb)
    # g - regular-green
    # r - red
    if value == "b":
        return(f"\033[1m{text}\033[0m")
    if value == "y":
        return(f"\033[1m\033[95m{text}\033[0m")
    if value == "g":
        reurn(f"\033[92m{text}\033[0m")
    if value == "r":
        return(f"\033[91m{text}\033[0m")

# Start
if __name__ == "__main__":

    # Not sure if there is any difference in using range(len()) instead?
    # This looks much cleaner anyway.

    for i in channels:
        getdata = Get_data(i)

    if (points > 0):
        print(f"{username} has {col('Total:', 'y')} {total_points} points")
    else:
        print(f"[{col('*', 'r')}] Could not find {col(username, 'y')} anywhere...\n")
