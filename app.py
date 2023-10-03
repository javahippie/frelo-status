from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from jinja2 import Environment, PackageLoader, select_autoescape
import sqlite3
import http.client
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stations.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class StationDetail(db.Model):
    id = db.Column(db.String(128), primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    short_name = db.Column(db.String(128), nullable=False)
    lat = db.Column(db.String(128), nullable=False)
    lon = db.Column(db.String(128), nullable=False)
    region_id = db.Column(db.String(128), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)


class StationStatus(db.Model):
    id = db.Column(db.String(128), primary_key=True)
    last_reported = db.Column(db.TIMESTAMP, primary_key=True)
    bikes_available = db.Column(db.Integer, nullable=False)
    docks_available = db.Column(db.Integer, nullable=False)
    is_installed = db.Column(db.Integer, nullable=False)
    is_renting = db.Column(db.Integer, nullable=False)
    is_returning = db.Column(db.Integer, nullable=False)


class WeatherStatus(db.Model):
    last_reported = db.Column(db.TIMESTAMP, primary_key=True)
    temperature_in_c = db.Column(db.Float, nullable=False)
    windspeed = db.Column(db.Float, nullable=False)
    weather_code = db.Column(db.Integer, nullable=False)


env = Environment(
    loader=PackageLoader("app"),
    autoescape=select_autoescape()
)


@app.route('/weather')
def retrieve_weather_details():
    with sqlite3.connect('instance/stations.db') as sql_connection:
        connection = http.client.HTTPSConnection('api.open-meteo.com')
        headers = {'Content-type': 'application/json'}
        connection.request('GET', '/v1/forecast?latitude=48.01164&longitude=7.82282&current_weather=true', None, headers)
        response = json.loads(connection.getresponse().read().decode())['current_weather']
    return response


@app.route('/station')
def retrieve_station_details():
    with sqlite3.connect('instance/stations.db') as sql_connection:
        connection = http.client.HTTPSConnection('gbfs.nextbike.net')
        headers = {'Content-type': 'application/json'}
        connection.request('GET', '/maps/gbfs/v1/nextbike_df/de/station_information.json', None, headers)
        response = json.loads(connection.getresponse().read().decode())
        cur = sql_connection.cursor()
        cur.execute('DELETE FROM station_detail')
        for status in response['data']['stations']:
            sql = '''INSERT INTO station_detail (ID, NAME, SHORT_NAME, LAT, LON, REGION_ID, CAPACITY)
                     VALUES (:station_id, :name, :short_name, :lat, :lon, :region_id, :capacity);'''
            if 'capacity' not in status:
                status['capacity'] = 0
            cur.execute(sql, status)
        sql_connection.commit()
    return response


@app.route('/status')
def retrieve_station_status():
    with sqlite3.connect('instance/stations.db') as sql_connection:
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
    return response


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@app.route('/xhr/<ts>')
def load_status_xhr(ts: int):
    with sqlite3.connect('instance/stations.db') as sql_connection:
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
                 where ((:ts is null and s.LAST_REPORTED = ((select max(LAST_REPORTED) from station_status))) 
                            or s.LAST_REPORTED = :ts)
                        and d.lat is not null and d.lon is not null'''
        cur = sql_connection.cursor()
        cur.execute(sql, {'ts': ts})
        rows = cur.fetchall()
    return rows


def load_report_times():
    sql = '''SELECT distinct last_reported, 
                             strftime('%d.%m.%Y, %H:%M', DATETIME(last_reported, 'unixepoch', 'localtime')) as readable
                from station_status
                order by last_reported asc;'''
    with sqlite3.connect('instance/stations.db') as sql_connection:
        sql_connection.row_factory = sqlite3.Row
        cur = sql_connection.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
    return rows


def load_station_history(station_id: str):
    with sqlite3.connect('instance/stations.db') as sql_connection:
        sql_connection.row_factory = dict_factory
        sql = '''SELECT strftime('%Y-%m-%d %H:00', DATETIME(s.last_reported, 'unixepoch', 'localtime')) date_time, avg(s.bikes_available) bikes_available, d.name
                 from station_status s
                 left join station_detail d
                 on s.id = d.id
                 where s.id = :station_id
                 GROUP BY strftime('%Y-%m-%d %H:00', DATETIME(s.last_reported, 'unixepoch', 'localtime'))
                 order by s.bikes_available desc;'''
        cur = sql_connection.cursor()
        cur.execute(sql, {'station_id': station_id})
        rows = cur.fetchall()
    return rows


@app.route('/')
def route_with_ts():
    return env.get_template("home.html").render({"report_times": load_report_times()})


@app.route('/history/<station_id>')
def route_history(station_id: str):
    station_history = load_station_history(station_id)
    return env.get_template("history.html").render({"history": station_history,
                                                    "max_bikes": station_history[0]['bikes_available'],
                                                    "station_name": station_history[0]['name']})


if __name__ == '__main__':
    app.run()
