import os
import unittest
from pymongo import MongoClient
import json

# It is important that the next two line be in that order (sorry PEP8)
# Flask seems to instantiate the dB with the second line
# And we want to make sure the environment variable is set before
os.environ['TESTING'] = "T"
from api import app


class APITestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

    def tearDown(self):
        client = MongoClient()
        client.drop_database(app.config["MONGO_DBNAME"])

    def test_get_all_documents(self):
        # try existing field
        rv = self.app.get('/problem')
        self.assertEqual(rv.status_code, 200)
        # try wrong field
        rv = self.app.get('/dummy_field')
        self.assertEqual(rv.status_code, 404)

    def test_create_problem(self):
        # existing field
        rv = self.app.post('/problem',
                           data=json.dumps({"uuid": "TT", "workflow": "TT"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        # wrong field
        rv = self.app.post('/dummy_field',
                           data=json.dumps({"uuid": "ha",
                                            "workflow": "never_written"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 404)
        # existing field but wrong key
        rv = self.app.post('/problem',
                           data=json.dumps({"dummy": "TT"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 400)
        


if __name__ == '__main__':
    unittest.main()
