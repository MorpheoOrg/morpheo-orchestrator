import unittest
from flask_pymongo import PyMongo
from pymongo import MongoClient
import api


class APITestCase(unittest.TestCase):

    def setUp(self):
        
        api.app.config['MONGO_DBNAME'] = 'test_db'
        api.app.config['TESTING'] = True
        # self.mongo = PyMongo(api.app)
        self.app = api.app.test_client()

    def test_get_all_documents(self):
        rv = self.app.get('/problem')
        print(api.mongo.db)
        self.assertEqual(rv.status_code, 200)

    def test_get_all_documenys(self):
        rv = self.app.get('/caca')
        self.assertEqual(rv.status_code, 200)

    def tearDown(self):
        client = MongoClient()
        client.drop_database('test_db')

if __name__ == '__main__':
    unittest.main()
