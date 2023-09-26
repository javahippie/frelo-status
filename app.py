from flask import Flask, Response
from jinja2 import Environment, PackageLoader, select_autoescape
import sqlite3
import http.client
import json

app = Flask(__name__)
env = Environment(
    loader=PackageLoader("app"),
    autoescape=select_autoescape()
)


@app.route('/station')
def retrieve_station_details():
    sql_connection = sqlite3.connect('database.db')
    connection = http.client.HTTPSConnection('gbfs.nextbike.net')
    headers = {'Content-type': 'application/json'}
    connection.request('GET', '/maps/gbfs/v1/nextbike_df/de/station_information.json', None, headers)
    response = json.loads(connection.getresponse().read().decode())
    for status in response['data']['stations']:
        sql = '''INSERT INTO station_detail (ID, NAME, SHORT_NAME, LAT, LON, REGION_ID, CAPACITY)
                 VALUES (:station_id, :name, :short_name, :lat, :lon, :region_id, :capacity);'''
        if 'capacity' not in status:
            status['capacity'] = 0
        cur = sql_connection.cursor()
        cur.execute(sql, status)
    sql_connection.commit()
    sql_connection.close()
    return response


@app.route('/status')
def retrieve_station_status():
    sql_connection = sqlite3.connect('database.db')
    connection = http.client.HTTPSConnection('gbfs.nextbike.net')
    headers = {'Content-type': 'application/json'}
    connection.request('GET', '/maps/gbfs/v1/nextbike_df/de/station_status.json', None, headers)
    response = json.loads(connection.getresponse().read().decode())
    for status in response['data']['stations']:
        sql = '''INSERT INTO station_status (ID, BIKES_AVAILABLE, DOCKS_AVAILABLE, IS_INSTALLED, IS_RENTING, IS_RETURNING, LAST_REPORTED)
                  VALUES (:station_id, :num_bikes_available, :num_docks_available, :is_installed, :is_renting, :is_returning, :last_reported);'''
        cur = sql_connection.cursor()
        cur.execute(sql, status)
    sql_connection.commit()
    sql_connection.close()
    return response


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@app.route('/xhr/<ts>')
def load_status_xhr(ts: int):
    sql_connection = sqlite3.connect('database.db')
    sql_connection.row_factory = dict_factory
    sql = '''SELECT s.ID, 
                    s.BIKES_AVAILABLE, 
                    s.DOCKS_AVAILABLE,
                    s.LAST_REPORTED,
                    d.NAME, 
                    d.LAT, 
                    d.LON, 
                    s.DOCKS_AVAILABLE + s.BIKES_AVAILABLE as BIKES_TOTAL, 
                    1.0 * s.BIKES_AVAILABLE / (s.BIKES_AVAILABLE + s.DOCKS_AVAILABLE) * 100  as BIKES_PERCENTAGE
             FROM station_status s
             LEFT JOIN station_detail d 
             ON s.ID = d.ID
             where (:ts is null and s.LAST_REPORTED = ((select max(LAST_REPORTED) from station_status))) 
                   or s.LAST_REPORTED = :ts'''
    cur = sql_connection.cursor()
    cur.execute(sql, {'ts': ts})
    rows = cur.fetchall()
    sql_connection.close()
    return rows


def load_report_times():
    sql_connection = sqlite3.connect('database.db')
    sql_connection.row_factory = sqlite3.Row
    sql = '''SELECT distinct last_reported, DATETIME(last_reported, 'unixepoch') as readable from station_status'''
    cur = sql_connection.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    sql_connection.close()
    return rows


@app.route('/')
def route_with_ts():
    return env.get_template("home.html").render({"report_times": load_report_times()})


if __name__ == '__main__':
    app.run()
