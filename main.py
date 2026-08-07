import os 

from database.connection import DatabaseConnection
project_directory = os.path.dirname(os.path.abspath(__file__))

db_path = os.path.join(project_directory,"data","observation.db")


connection = DatabaseConnection(db_path)

schema_path = os.path.join(project_directory,"database","createtable.sql")

with open(schema_path,"r") as file:
    sql_script = file.read()
connection.execute(sql_script)
connection.commit()