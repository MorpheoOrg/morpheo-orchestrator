import os
import unittest
import json
import time
from pymongo import MongoClient

# It is important that the next two line be in that order (sorry PEP8)
# Flask seems to instantiate the dB with the second line
# And we want to make sure the environment variable is set before
os.environ['TESTING'] = "T"
from api import app
from api import list_collection
from tasks import size_batch_update


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
                           data=json.dumps({"uuid": "P1", "workflow": "W1",
                                            "test_dataset": ["TD1", "TD2"],
                                            "size_train_dataset": 4}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        # wrong field
        rv = self.app.post('/dummy_field',
                           data=json.dumps({"uuid": "ha",
                                            "workflow": "never_written",
                                            "test_dataset": ["TD1", "TD2"],
                                            "size_train_dataset": 4}),
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
                           data=json.dumps({"uuid": "P2", "workflow": "W2",
                                            "test_dataset": ["TD1", "TD2"],
                                            "size_train_dataset": 4}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        # add data for this problem and check there is no new learnuplet
        # as no algo have been uploaded
        nb_data = 10
        rv = self.app.post('/data',
                           data=json.dumps({"uuid": ["D%s" % i
                                                     for i in range(nb_data)],
                                            "problems": ["P1", "P2"]}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(
            json.loads(rv.get_data(as_text=True))["new_learnuplets"], 0)
        # add algo
        rv = self.app.post('/algo',
                           data=json.dumps({"uuid": "A1", "problem": "P2"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        # check learnuplet were created
        self.assertEqual(self.db.learnuplet.find({"model": "A1"}).count(), 1)


    def test_create_data(self):
        n_data = 10
        n_data_new = 10
        # add associated problem first
        self.db.problem.insert_one({"uuid": "P3", "workflow": "W3",
                                    "test_dataset": ["TD1", "TD2"],
                                    "size_train_dataset": n_data_new / 2})
        # add "preexisting" data
        self.db.data.insert_many([{"uuid": "DD%s" % i, "problems": "P3",
                                   "timestamp_upload": int(time.time())}
                                  for i in range(n_data)])
        # add algo
        self.db.algo.insert_many([{"uuid": "A3_%s" % i, "problem": "P3",
                                   "timestamp_upload": int(time.time())}
                                  for i in ["tofill", "donup"]])
        # add learnuplet with status tofill and already trained
        self.db.learnuplet.insert_many([{"train_data": ["DD1"],
                                         "test_data": ["TT1"], "problem": "P3",
                                         "model": "A3_tofill", "worker": None,
                                         "perf": None, "status": "tofill"},
                                        {"train_data": ["DD%s" % i
                                                  for i in range(n_data)],
                                         "test_data": ["TT1"],
                                         "problem": "P3",
                                         "model": "A3_donup", "worker": None,
                                         "perf": None, "status": "donup"}])
        # add new data and check if learnuplets are correctly updated
        rv = self.app.post('/data',
                           data=json.dumps({"uuid": ["D3%s" % i for i
                                                     in range(n_data_new)],
                                            "problems": ["P3"]}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(
            json.loads(rv.get_data(as_text=True))["new_learnuplets"], 2)
        self.assertEqual(self.db.learnuplet.find({"problem": "P3"}).count(), 3)
        if n_data_new + 1 > size_batch_update:
            self.assertEqual(
                self.db.learnuplet.find({"problem": "P3", "status": "todo"}).
                count(), 2)

    def test_request_prediction(self):
        # add learnuplet
        self.db.learnuplet.insert_many([{"train_data": ["DL%s" % i for i
                                                  in range(size_batch_update)],
                                         "problem": "PP", "test_data": ["TT1"],
                                         "model": "AP1", "worker": "bobor",
                                         "perf": 0.96, "status": "donup"},
                                        {"train_data": ["DL%s" % i for i
                                                  in range(size_batch_update)],
                                         "problem": "PP", "test_data": ["TT2"],
                                         "model": "AP2", "worker": "bobor",
                                         "perf": 0.98, "status": "donup"}])
        # request possible prediction and check preduplet has been created
        rv = self.app.post('/prediction',
                           data=json.dumps({"data": ["DP%s" % i
                                                     for i in range(10)],
                                            "problem": "PP"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(self.db.preduplet.find({"problem": "PP",
                                                 "status": "todo"}).count(), 1)
        # wrong key in request
        rv = self.app.post('/prediction',
                           data=json.dumps({"problem": "PP"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 400)
        # non existing model or problem
        rv = self.app.post('/prediction',
                           data=json.dumps({"data": ["DPB1"],
                                            "problem": "IDONTEXIST"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 400)



if __name__ == '__main__':
    unittest.main()
