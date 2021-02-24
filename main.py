import requests
import json
from datetime import datetime, timedelta
from sys import argv
import argparse
import sqlite3 as sl

# Rosh: 592b0d5610b3f73ce98ace4c

class load:

    def __init__(self, chname, luser):
        self.load_user = luser #str(argv[1])
        self.channel_name = chname

        self.db_name = 'data.db'
        self.printout = 0

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

        getdb = db(self.db_name)
        getdb.insert_db(j['displayName'], self.points, self.realtime, self.rank, self.username)


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

        if (self.printout == 1):
            self.print_data()
        else:
            return

    def print_data(self):
            print("Username: {} \nPoints: {} \nATH: {} \nWatchtime: {} \nRank: {}".format(
                        self.username,
                        self.points,
                        self.pointsAlltime,
                        self.realtime,
                        self.rank)
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
        self.get_id(self.channel_name)



class db:

    def __init__(self, master):
        self.db_name = "data.db"
        self.connect()

    def connect(self):
        self.con = sl.connect(self.db_name)
        self.c = self.con.cursor()

    def disconnect(self):
        self.c.close()


    def check_table(self):
        with self.con:
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS Channels (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    points INTEGER,
                    watchtime TEXT,
                    rank TEXT,
                    user TEXT
                );
            """)
        self.disconnect()

    def insert_db(self, name, points, watchtime, rank, user):
        sql_update = """UPDATE Channels SET name = ?, points = ?, watchtime = ?, rank = ?, user = ? WHERE name = ?"""
        sql_insert = 'INSERT INTO Channels (id, name, points, watchtime, rank, user) values(?, ?, ?, ?, ?, ?)'
        data_update = [(name, points, watchtime, rank, user, name)]
        data_insert = [(None, name, points, watchtime, rank, user)]

        with self.con:
            # Update or insert depending if row with name exists.
            for row in self.con.execute("SELECT name FROM Channels WHERE name=?", (name,)):
                name = row
                print("[-] {} Found. Updating existing row".format(name[0]))
                self.con.executemany(sql_update, data_update)
                break
            else:
                print("[-] {} Not found. Insert new row".format(name[0]))
                self.con.executemany(sql_insert, data_insert)
        self.disconnect()


    def del_row(self, name):
        print("Removing: {}".format(name))
        sql_del = 'DELETE FROM Channels WHERE name=?'
        data = [(name)]
        with self.con:
            self.con.execute(sql_del, data)
        self.disconnect()

    def update_all(self):
        with self.con:
            data = self.con.execute("SELECT name FROM Channels")
            for row in data:
                print(row[0])
        self.disconnect()

    def print_db(self):
        with self.con:
            data = self.con.execute("SELECT * FROM Channels")
            for row in data:
                print("------{}------\nUsername: {}\nPoints: {}\nWatchtime: {}\nRank: {}".format(
                            row[1],
                            row[5],
                            row[4],
                            row[3],
                            row[2])
                        )
        self.disconnect()


def main():
    parser = argparse.ArgumentParser(prog='main.py')
    parser.add_argument('-u', help='username', required=True)
    parser.add_argument('-c', help='channel', required=True)
    parser.add_argument('-d', help='delete channel from database')
    parser.add_argument('-o', help='update all')
    args = parser.parse_args()
    start(args.c, args.u)

    if args.d:
        getdb = db("data.db")
        getdb.del_row(args.d)

    if args.o:
        getdb = db("data.db")
        getdb.update_all()

def start(argu, argc):
    getdata = load(argu, argc)
    getdata.init()

    getdb = db("data.db")
    getdb.check_table()
    getdb.print_db()

main()
