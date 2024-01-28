from urllib.request import urlopen
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import json
import csv
from arcgis.gis import GIS
from arcgis.features import GeoAccessor, FeatureLayer
import pandas as pd


def get_stations_metadata(data):
    stations = {}
    for d in data:
        station_id = d["id"]
        gegrLat = d["gegrLat"]
        gegrLon = d["gegrLon"]
        #name = d["city"]["name"]
        #province = d["city"]["commune"]["provinceName"]
        stations[station_id] = {"lat": gegrLat, "lon": gegrLon}
    return(stations)

def get_newest_value(data, number):
    # print(data["values"][number]["value"])
    if (str(data["values"][number]["value"]) == "None"):
        return (get_newest_value(data, number + 1))
    else:
        return (data["values"][number]["value"], number, data["values"][number]["date"])

def get_measured_values(id):
    number = 0
    url = "https://api.gios.gov.pl/pjp-api/rest/data/getData/" + str(id)
    response = urlopen(url)
    data = json.loads(response.read())

    val, n, date = get_newest_value(data, number)
    return (val, date)

    # print(json.dumps(data, indent = 4, sort_keys=True))

def get_sensor_data(id, paramCodes):
    url = "https://api.gios.gov.pl/pjp-api/rest/station/sensors/" + str(id)
    response = urlopen(url)
    data = json.loads(response.read())
    # print(json.dumps(data, indent = 4, sort_keys=True))

    for d in data:
        if (d["param"]["paramCode"] in paramCodes):
            try:
                val, date_time = get_measured_values(d["id"])
                date, t = date_time.split(' ')
                time = date + "_"  + t;
                return (
                d["id"], d["param"]["paramCode"], val, date, time)  # zwraca: idSensora, nazwa mierzonego parametru
            except:
                pass

def write_to_csv(sensors, headers):
    with open('dane_z_sensorow_3.csv', 'w', newline='') as file:
        writer = csv.writer(file)

        writer.writerow(headers)

        for k in list(sensors.keys()):
            l = k, sensors[k]["stationId"], sensors[k]["lon"], sensors[k]["lat"], sensors[k]["param"], sensors[k]["value"], sensors[k]["time"]
            writer.writerow(l)

def get_data_for_all_sensors(stations,stations_id, param_codes):
    sensors = {}
    for station_id in stations_id:
        try:
            for param_code in param_codes:
                id, param, val, date, time = get_sensor_data(station_id, param_code)
                sensors[id] = {"param": param, "stationId": station_id, "lon": stations[station_id]["lon"],
                            "lat": stations[station_id]["lat"], "value": val, "date": date, "time": time}
        except:
            pass
    return(sensors)


sched = BlockingScheduler()



@sched.scheduled_job('interval', seconds=1800)
def timed_job():
    try:
        url = "https://api.gios.gov.pl/pjp-api/rest/station/findAll"
        response = urlopen(url)
        data = json.loads(response.read())

        # print(json.dumps(data, indent = 4, sort_keys=True))

        # pozyskanie szczegolowych informacji o stacjach i zapisanie do zmiennej
        stations = get_stations_metadata(data)

        param_codes = ["SO2", "PM10", "PM2.5"]  # lista z wyszukiwanymi parametrami
        stations_id = list(stations.keys())  # zapisanie kluczy hashmapy "stations" do listy
        sensors = get_data_for_all_sensors(stations, stations_id,
                                       param_codes)  # wyciagniecie danych z kazdego sensora i zapisanie do hashmapy

        # headery do pliku csv
        headers = ("Id_sensora", "Id_stacji", "longitude", "latitude", "parametr", "wartosc", "data_pomiaru")

        # Zapisanie danych z sensorow do pliku csv
        write_to_csv(sensors, headers)


        #odczytanie danych do logowanie
        f = open('logowanie.json')
        logowanie = json.load(f)


        gis = GIS("http://www.arcgis.com", logowanie["login"], logowanie["haslo"])
        table_url = "https://services2.arcgis.com/MzCtPDSne0rpIt7V/arcgis/rest/services/dane_z_sensorow_3/FeatureServer/0"

        tbl = FeatureLayer(table_url, gis=gis)
        tbl.manager.truncate()

        casos_csv = r'dane_z_sensorow_3.csv'

        df = GeoAccessor.from_table(casos_csv)

        sedf = pd.DataFrame.spatial.from_xy(df=df, x_column='longitude', y_column='latitude', sr=4326)

        adds = sedf.spatial.to_featureset()
        tbl.edit_features(adds=adds)


        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

        print(f"Pomyslnie dodano dane: ", dt_string)

    except Exception as e:
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        print("ERROR: {e}", dt_string)
        pass


sched.start()