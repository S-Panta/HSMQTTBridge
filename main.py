import time
import os
from dotenv import load_dotenv

from database.connection import DatabaseConnection

# from hydroserver.request import Observation
from mqtt.consumer import MQTTClient
from hydroserver.publisher import HydroServerPublisher

load_dotenv()
HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
API_KEY = os.getenv("HYDROSERVER_API_KEY")

project_directory = os.path.dirname(os.path.abspath(__file__))

db_path = os.path.join(project_directory, "data", "observation.db")

connection = DatabaseConnection(db_path)

schema_path = os.path.join(project_directory, "database", "createtable.sql")

with open(schema_path, "r", encoding="utf-8") as file:
    sql_script = file.read()
connection.execute(sql_script)
connection.commit()

HOST = "raspberrypi1.mypc.usu.edu"
PORT = 1883
# Conect to mqtt
client = MQTTClient(HOST, PORT)


# try:
#     client.connect()
#     while True:
#         time.sleep(5)
# except KeyboardInterrupt:
#     print("mqtt client stopped")
#     client.stop()

publisher = HydroServerPublisher(HYDROSERVER_URL, API_KEY)
invalid_payload = {
    "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d682"},
    "result": 32.1,
    "phenomenonTime": "2026-08-06T17:43:34Z",
}
valid_payload = {
    "Datastream": {"@iot.id": "019eae3f-3450-70db-b5d2-a55879b4d681"},
    "result": 32.1,
    "phenomenonTime": "2026-08-06T17:43:34Z",
}
# print(publisher.post_observation_to_hydroserver(invalid_payload))
# # print("...................................................")
print(publisher.post_observation_to_hydroserver(invalid_payload))
