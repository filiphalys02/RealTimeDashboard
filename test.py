from urllib.request import urlopen
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import json
import csv
from arcgis.gis import GIS
from arcgis.features import GeoAccessor, FeatureLayer


# Connect to ArcGIS Online
f = open('logowanie.json')
logowanie = json.load(f)
gis = GIS("http://www.arcgis.com", logowanie["login"], logowanie["haslo"])

# Specify the path to your CSV file
csv_file_path = r"dane_z_sensorow_3.csv"

# Specify the name for the hosted feature layer on ArcGIS Online
feature_layer_name = "stan_powietrza3"

# Read the CSV file and create a feature layer
try:
    # Read the CSV file and create a feature layer
    csv_item = gis.content.add({}, csv_file_path)
    csv_feature_layer = csv_item.publish()

    # Rename the hosted feature layer
    csv_feature_layer.update({'title': feature_layer_name})

    print(f"Successfully uploaded and published")

except Exception as e:
    print(f"Error uploading CSV data: {e}")
