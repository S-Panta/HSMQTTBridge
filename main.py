import time
import os

from database.connection import DatabaseConnection
from mqtt.consumer import MQTTClient

project_directory = os.path.dirname(os.path.abspath(__file__))

db_path = os.path.join(project_directory, "data", "observation.db")

connection = DatabaseConnection(db_path)

schema_path = os.path.join(project_directory, "database", "createtable.sql")

with open(schema_path, "r", encoding="utf-8") as file:
    sql_script = file.read()
connection.execute(sql_script)
connection.commit()

HOST = "localhost"
PORT = 1883
# Conect to mqtt
client = MQTTClient(HOST, PORT)

try:
    client.connect()
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    print("mqtt client stopped")
    client.stop()
