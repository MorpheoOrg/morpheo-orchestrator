import os
import unittest
from pymongo import MongoClient
import json

# It is important that the next two line be in that order (sorry PEP8)
# Flask seems to instantiate the dB with the second line
# And we want to make sure the environment variable is set before
os.environ['TESTING'] = "T"
from api import app
from api import list_collection
from tasks import size_batch


class APITestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.app = app.test_client()
        self.client = MongoClient()
        self.db = self.client[app.config["MONGO_DBNAME"]]

    @classmethod
    def tearDownClass(self):
        self.client.drop_database(app.config["MONGO_DBNAME"])

    def test_get_all_documents(self):
        # try existing collection
        for collection_name in list_collection:
            rv = self.app.get('/%s' % collection_name)
            self.assertEqual(rv.status_code, 200)
        # try wrong collection
        rv = self.app.get('/dummy_field')
        self.assertEqual(rv.status_code, 404)

    def test_create_problem(self):
        # existing field
        rv = self.app.post('/problem',
                           data=json.dumps({"uuid": "P1", "workflow": "W1"}),
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
                           data=json.dumps({"dummy": "ho"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 400)

    def test_create_algo(self):
        # add associated problem first
        rv = self.app.post('/problem',
                           data=json.dumps({"uuid": "P2", "workflow": "W2"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        # add data for this problem. TODO change api to send list of data...
        nb_data = 10
        for i in range(nb_data):
            rv = self.app.post('/data',
                               data=json.dumps({"uuid": "D%s" % i,
                                                "problems": ["P1", "P2"]}),
                               content_type='application/json')
            self.assertEqual(rv.status_code, 201)
        # add algo
        rv = self.app.post('/algo',
                           data=json.dumps({"uuid": "A1", "problem": "P2"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        # check learnuplet were created
        nb_learnuplet = nb_data // size_batch
        if nb_data % size_batch > 0:
            nb_learnuplet += 1
        self.assertEqual(self.db.learnuplet.find().count(), nb_learnuplet)



if __name__ == '__main__':
    unittest.main()
