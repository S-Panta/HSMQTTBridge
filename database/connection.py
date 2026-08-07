import sqlite3


class DatabaseConnection:
    """Class to wrap sqlite connection"""

    def __init__(self, path):
        self.path = path
        self.connection = None

    # lazy initialization
    def __connect(self):
        if self.connection is None:
            try:
                self.connection = sqlite3.connect(self.path)
                self.connection.execute("PRAGMA journal_mode = WAL")
                print("Connection successful")
            except sqlite3.Error as e:
                print(f"Error connecting to database: {e}")

    def execute(self, sql_script):
        self.__connect()
        cursor = self.connection.cursor()
        cursor.execute(sql_script)

    def commit(self):
        self.connection.commit()
