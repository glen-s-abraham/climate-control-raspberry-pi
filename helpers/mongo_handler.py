from pymongo import MongoClient
from pymongo.errors import PyMongoError

class MongoHandler:
    def __init__(self, url, db_name, collection_name):
        self.client = MongoClient(url)
        self.connected = self.test_connection()
        self.db = self.client[db_name] if self.connected else None
        self.collection = self.db[collection_name] if self.connected else None

    def test_connection(self):
        try:
            self.client.admin.command('ismaster')
            return True
        except PyMongoError:
            return False

    def insert_data(self, data):
        if not self.connected:
            if not self.test_connection():
                return False  # Connection is still not established.
            self.connected = True
            # Reinitialize db and collection since connection is now established.
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]

        try:
            self.collection.insert_one(data)
            return True
        except PyMongoError as e:
            print(f"Failed to insert data into MongoDB: {e}")
            return False