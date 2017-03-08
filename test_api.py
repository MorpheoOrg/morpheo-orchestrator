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


def generate_list_learnuplets(n_learnuplet, n_train=5, n_test=5, problem="PB",
                              status="todo", perf=None, worker=None,
                              model_prefix="MD_", uuid_prefix="id_"):
    if type(perf) is not list:
        perf = [perf] * n_learnuplet
    list_learnuplets = [
        {"problem": problem, "worker": worker, "perf": perf[j],
         "status": status, "model": "%s%s" % (model_prefix, j),
         "train_data": ["D%s%s" % (i, j) for i in range(n_train)],
         "test_data": ["DT%s%s" % (i, j) for i in range(n_test)],
         "uuid": "%s%s" % (uuid_prefix, j)}
        for j in range(n_learnuplet)]
    return list_learnuplets


def generate_list_preduplets(n_preduplet, n_data=4, problem="PB", model="MD",
                            worker=None, status="todo", uuid_prefix="id_",
                            timestamp_request=None, timestamp_done=None):
    if not timestamp_request:
        timestamp_request = int(time.time())
    list_preduplets = [
        {"problem": problem, "worker": worker, "status": status, "model": model,
         "data": ["T%s%s" % (i, j) for i in range(n_data)],
         "timestamp_request": timestamp_request,
         "timestamp_done": timestamp_done,
         "uuid": "%s%s" % (uuid_prefix, j)}
        for j in range(n_preduplet)]
    return list_preduplets


class APITestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.client = MongoClient()
        self.db = self.client[app.config["MONGO_DBNAME"]]

    def tearDown(self):
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
        # TODO do we need it?? Make it similar to generate_list_learnuplets
        self.db.data.insert_many([{"uuid": "DD%s" % i, "problems": "P3",
                                   "timestamp_upload": int(time.time())}
                                  for i in range(n_data)])
        # add algo
        self.db.algo.insert_many([{"uuid": "A3_%s" % i, "problem": "P3",
                                   "timestamp_upload": int(time.time())}
                                  for i in ["tofill", "done"]])
        # add learnuplet with status tofill and already trained
        learnuplet_tofill = generate_list_learnuplets(
            1, n_train=1, n_test=1, problem="P3", model_prefix="Atofill",
            status="tofill")
        learnuplet_done = generate_list_learnuplets(
            1, n_train=n_data, n_test=1, problem="P3", model_prefix="Adone",
            worker="WW", perf=0.99, status="done")
        self.db.learnuplet.insert_many(learnuplet_tofill + learnuplet_done)
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
        learnuplets = generate_list_learnuplets(
            2, n_train=size_batch_update, n_test=1, problem="PP",
            worker="bobor", status="done", perf=[0.96, 0.98])
        self.db.learnuplet.insert_many(learnuplets)
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

    def test_set_uplet_worker(self):
        # add learnuplet and preduplet
        learnuplet = generate_list_learnuplets(1, uuid_prefix="id_")[0]
        self.db.learnuplet.insert_one(learnuplet)
        preduplet = generate_list_preduplets(1, uuid_prefix="id_")[0]
        self.db.preduplet.insert_one(preduplet)
        for uplet in ['learnuplet', 'preduplet']:
            # good request
            rv = self.app.post('/worker/%s/id_0' % uplet,
                               data=json.dumps({"worker": "bobor"}),
                               content_type='application/json')
            self.assertEqual(rv.status_code, 200)
            collection = self.db[uplet]
            self.assertEqual(collection.find({"uuid": "id_0",
                                              "worker": "bobor"}).count(), 1)
            # wrong key in request
            rv = self.app.post('/worker/%s/id_0' % uplet,
                               data=json.dumps({"rocker": "oups"}),
                               content_type='application/json')
            self.assertEqual(rv.status_code, 400)
        # wrong uplet name
        rv = self.app.post('/worker/uplet/id_0',
                           data=json.dumps({"worker": "oups"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 404)

    def test_update_learnuplet(self):
        # add learnuplet
        learnuplet = generate_list_learnuplets(
            1, uuid_prefix="id_", status="pending", worker="bobor")[0]
        self.db.learnuplet.insert_one(learnuplet)
        # should be ok
        rv = self.app.post('/learndone/id_0',
                           data=json.dumps({"status": "done", "perf": 0.9}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(self.db.learnuplet.find({"uuid": "id_0",
                                                  "perf": 0.9}).count(), 1)
        # wrong key in request
        rv = self.app.post('/learndone/id_0',
                           data=json.dumps({"sttys": "oups", "perf": 0.9}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 400)

    def test_update_preduplet(self):
        # add preduplet
        preduplet = generate_list_preduplets(
            1, uuid_prefix="id_", status="pending", worker="bobor")[0]
        self.db.preduplet.insert_one(preduplet)
        # should be ok
        rv = self.app.post('/preddone/id_0',
                           data=json.dumps({"status": "done"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(self.db.preduplet.find({"uuid": "id_0",
                                                  "status": "done"}).count(), 1)
        # wrong key in request
        rv = self.app.post('/preddone/id_0', data=json.dumps({"sttys": "oups"}),
                           content_type='application/json')
        self.assertEqual(rv.status_code, 400)


if __name__ == '__main__':
    unittest.main()
