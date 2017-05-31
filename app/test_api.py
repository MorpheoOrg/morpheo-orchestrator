#!/usr/bin/env python3

'''
 Copyright Morpheo Org. 2017

 contact@morpheo.co

 This software is part of the Morpheo project, an open-source machine
 learning platform.

 This software is governed by the CeCILL license, compatible with the
 GNU GPL, under French law and abiding by the rules of distribution of
 free software. You can  use, modify and/ or redistribute the software
 under the terms of the CeCILL license as circulated by CEA, CNRS and
 INRIA at the following URL "http://www.cecill.info".

 As a counterpart to the access to the source code and  rights to copy,
 modify and redistribute granted by the license, users are provided only
 with a limited warranty  and the software's author,  the holder of the
 economic rights,  and the successive licensors  have only  limited
 liability.

 In this respect, the user's attention is drawn to the risks associated
 with loading,  using,  modifying and/or developing or reproducing the
 software by the user in light of its specific status of free software,
 that may mean  that it is complicated to manipulate,  and  that  also
 therefore means  that it is reserved for developers  and  experienced
 professionals having in-depth computer knowledge. Users are therefore
 encouraged to load and test the software's suitability as regards their
 requirements in conditions enabling the security of their systems and/or
 data to be ensured and,  more generally, to use and operate it in the
 same conditions as regards security.

 The fact that you are presently reading this means that you have had
 knowledge of the CeCILL license and that you accept its terms.
'''

import os
import unittest
import json
import time
import numpy as np
from pymongo import MongoClient
from base64 import b64encode


# It is important that the next two line be in that order (sorry PEP8)
# Flask seems to instantiate the dB with the second line
# And we want to make sure the environment variable is set before
os.environ['TESTING'] = "T"
os.environ['USER_AUTH'] = "test"
os.environ['PWD_AUTH'] = "test"
from api import app
from api import list_collection

headers = {
    'Authorization': 'Basic %s' % b64encode(b"test:test").decode("ascii")
}
print(headers)

def generate_list_learnuplets(n_learnuplet, n_train=5, n_test=5, problem="PB",
                              status="todo", perf=None, worker=None,
                              algo_prefix="MD_", model_prefix="MD_",
                              uuid_prefix="id_", rank=0,
                              timestamp_creation=None, timestamp_done=None):
    if type(perf) is not list:
        perf = [perf] * n_learnuplet
    if not timestamp_creation:
        timestamp_creation = int(time.time())
    if rank == 0 and algo_prefix != model_prefix:
        algo_prefix = model_prefix
    if status == "done":
        train_perf = list(np.random.randn(n_train))
        test_perf = list(np.random.randn(n_test))
    else:
        train_perf = None
        test_perf = None
    list_learnuplets = [
        {"problem": problem, "worker": worker, "perf": perf[j],
         "train_perf": train_perf, "test_perf": test_perf,
         "status": status, "algo": "%s%s_s" % (algo_prefix, j),
         "model_start": "%s%s_s" % (model_prefix, j),
         "model_end": "%s%s_e" % (model_prefix, j), "rank": rank,
         "train_data": ["D%s%s" % (i, j) for i in range(n_train)],
         "test_data": ["DT%s%s" % (i, j) for i in range(n_test)],
         "uuid": "%s%s" % (uuid_prefix, j), "timestamp_done": timestamp_done,
         "timestamp_creation": timestamp_creation}
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
            rv = self.app.get('/%s' % collection_name, headers=headers)
            self.assertEqual(rv.status_code, 200)
        # try wrong collection
        rv = self.app.get('/dummy_field', headers=headers)
        self.assertEqual(rv.status_code, 404)

    def test_create_problem(self):
        # existing field
        rv = self.app.post('/problem',
                           data=json.dumps({"uuid": "P1", "workflow": "W1",
                                            "test_dataset": ["TD1", "TD2"],
                                            "size_train_dataset": 4}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 201)
        # existing field but wrong key
        rv = self.app.post('/problem',
                           data=json.dumps({"dummy": "ho"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)

    def test_create_algo(self):
        # add associated problem first
        rv = self.app.post('/problem',
                           data=json.dumps({"uuid": "P2", "workflow": "W2",
                                            "test_dataset": ["TD1", "TD2"],
                                            "size_train_dataset": 4}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 201)
        # add data for this problem and check there is no new learnuplet
        # as no algo have been uploaded
        nb_data = 10
        rv = self.app.post('/data',
                           data=json.dumps({"uuid": ["D%s" % i
                                                     for i in range(nb_data)],
                                            "problems": ["P2"]}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(
            json.loads(rv.get_data(as_text=True))["new_learnuplets"], 0)
        # try to add algo associated with non-existing problem
        rv = self.app.post('/algo',
                           data=json.dumps({"uuid": "A", "problem": "EMPTY"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)
        # add algo
        rv = self.app.post('/algo',
                           data=json.dumps({"uuid": "A", "problem": "P2"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 201)
        # check learnuplet were created
        self.assertEqual(self.db.learnuplet.find({"algo": "A"}).count(), 3)
        learnuplet_0 = self.db.learnuplet.find_one({"model_start": "A",
                                                    "rank": 0})
        self.assertEqual(learnuplet_0["status"], "todo")
        self.assertEqual(self.db.learnuplet.
                         find_one({"model_start": '',
                                   "rank": 1})["status"], "todo")

    def test_create_data(self):
        n_data = 10
        n_data_new = 10
        # add associated problem first
        self.db.problem.insert_one({"uuid": "P3", "workflow": "W3",
                                    "test_dataset": ["TD1", "TD2"],
                                    "size_train_dataset": n_data_new // 2})
        # add "preexisting" data
        # TODO do we need it?? Make it similar to generate_list_learnuplets
        self.db.data.insert_many([{"uuid": "DD%s" % i, "problems": "P3",
                                   "timestamp_upload": int(time.time())}
                                  for i in range(n_data)])
        # add algo
        self.db.algo.insert_many([{"uuid": "A3_0", "problem": "P3",
                                   "timestamp_upload": int(time.time())}])
        # add learnuplet which are already trained
        learnuplet_done = generate_list_learnuplets(
            1, n_train=n_data, n_test=1, problem="P3", model_prefix="A3",
            worker="WW", perf=0.99, status="done")
        self.db.learnuplet.insert_many(learnuplet_done)
        # try to add data associated with non-existing problem
        rv = self.app.post('/data',
                           data=json.dumps({"uuid": ["D3%s" % i for i
                                                     in range(n_data_new)],
                                            "problems": ["EMPTY"]}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)
        # add data
        rv = self.app.post('/data',
                           data=json.dumps({"uuid": ["D3%s" % i for i
                                                     in range(n_data_new)],
                                            "problems": ["P3"]}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(
            json.loads(rv.get_data(as_text=True))["new_learnuplets"], 2)
        self.assertEqual(self.db.learnuplet.find({"problem": "P3"}).count(), 3)
        self.assertEqual(self.db.learnuplet.find({"problem": "P3",
                                                  "status": "todo",
                                                  "model_start": {"$ne":''}}).count(), 1)
        self.assertEqual(
            self.db.learnuplet.find({"problem": "P3",
                                     "status": "todo",
                                     "model_start": ''}).count(), 1)

    def test_request_prediction(self):
        # add learnuplet
        learnuplets = generate_list_learnuplets(
            2, n_train=5, n_test=1, problem="PP",
            worker="  ", status="done", perf=[0.96, 0.98])
        self.db.learnuplet.insert_many(learnuplets)
        # request possible prediction and check preduplet has been created
        rv = self.app.post('/prediction',
                           data=json.dumps({"data": ["DP%s" % i
                                                     for i in range(10)],
                                            "problem": "PP"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(self.db.preduplet.find({"problem": "PP",
                                                 "status": "todo"}).count(), 1)
        # wrong key in request
        rv = self.app.post('/prediction',
                           data=json.dumps({"problem": "PP"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)
        # non existing model or problem
        rv = self.app.post('/prediction',
                           data=json.dumps({"data": ["DPB1"],
                                            "problem": "IDONTEXIST"}),
                           content_type='application/json',
                           headers=headers)
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
                               content_type='application/json',
                               headers=headers)
            self.assertEqual(rv.status_code, 200)
            collection = self.db[uplet]
            self.assertEqual(collection.find({"uuid": "id_0",
                                              "worker": "bobor"}).count(), 1)
            # learnuplet uuid does not exist
            rv = self.app.post('/worker/%s/ad_0' % uplet,
                               data=json.dumps({"worker": "bobor"}),
                               content_type='application/json',
                               headers=headers)
            self.assertEqual(rv.status_code, 400)
            # wrong key in request
            rv = self.app.post('/worker/%s/id_0' % uplet,
                               data=json.dumps({"rocker": "oups"}),
                               content_type='application/json',
                               headers=headers)
            self.assertEqual(rv.status_code, 400)
        # wrong uplet name
        rv = self.app.post('/worker/uplet/id_0',
                           data=json.dumps({"worker": "oups"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 404)

    def test_report_perf_learnuplet_1(self):
        n_train = 5
        n_test = 5
        train_perf = {'%s' % i: j for i, j
                      in enumerate(list(np.random.randn(n_train)))}
        test_perf = {'%s' % i: j for i, j
                     in enumerate(list(np.random.randn(n_test)))}
        # add learnuplets
        learnuplet = generate_list_learnuplets(
            1, n_train=n_train, n_test=n_test, uuid_prefix="id_",
            status="pending", worker="bobor")[0]
        self.db.learnuplet.insert_one(learnuplet)
        # should be ok
        rv = self.app.post('/learndone/id_0',
                           data=json.dumps({"status": "done", "perf": 0.9,
                                            "train_perf": train_perf,
                                            "test_perf": test_perf}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(self.db.learnuplet.find({"uuid": "id_0",
                                                  "perf": 0.9}).count(), 1)
        # wrong learnuplet uuid
        rv = self.app.post('/learndone/ad_0',
                           data=json.dumps({"status": "done", "perf": 0.9,
                                            "train_perf": train_perf,
                                            "test_perf": test_perf}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)
        # wrong key in request
        rv = self.app.post('/learndone/id_0',
                           data=json.dumps({"sttys": "oups", "perfff": 0.9}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)

    def test_report_perf_learnuplet_2(self):
        n_train = 5
        n_test = 5
        train_perf = {'%s' % i: j for i, j
                      in enumerate(list(np.random.randn(n_train)))}
        test_perf = {'%s' % i: j for i, j
                     in enumerate(list(np.random.randn(n_test)))}
        # add learnuplets
        learnuplet_list = generate_list_learnuplets(
            1, n_train=n_train, n_test=n_test, uuid_prefix="id0_",
            status="done", rank=0, worker="bobor")
        learnuplet_list += generate_list_learnuplets(
            1, n_train=n_train, n_test=n_test, uuid_prefix="id1_",
            status="done", rank=1, worker="bobor")
        learnuplet_list += generate_list_learnuplets(
            1, n_train=n_train, n_test=n_test, uuid_prefix="id2_",
            status="pending", rank=2, worker="bobor", model_prefix='B')
        learnuplet_list += generate_list_learnuplets(
            1, n_train=n_train, n_test=n_test, uuid_prefix="id3_",
            status="todo", rank=3, worker="bobor", model_prefix='N')
        for learnuplet in learnuplet_list:
            self.db.learnuplet.insert_one(learnuplet)
        # should be ok
        rv = self.app.post('/learndone/id2_0',
                           data=json.dumps({"status": "failed"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 200)
        rv = self.app.post('/learndone/id2_0',
                           data=json.dumps({"status": "done", "perf": 0.9,
                                            "train_perf": train_perf,
                                            "test_perf": test_perf}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(self.db.learnuplet.find({"uuid": "id2_0",
                                                  "perf": 0.9}).count(), 1)
        self.assertEqual(self.db.learnuplet.find({"uuid": "id3_0",
                                                  "status": 'todo',
                                                  "model_start": 'B0_e'})
                         .count(), 1)

    def test_update_preduplet(self):
        # add preduplet
        preduplet = generate_list_preduplets(
            1, uuid_prefix="id_", status="pending", worker="bobor")[0]
        self.db.preduplet.insert_one(preduplet)
        # should be ok
        rv = self.app.post('/preddone/id_0',
                           data=json.dumps({"status": "done"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(self.db.preduplet.find({"uuid": "id_0",
                                                 "status": "done"}).count(), 1)
        # wrong learnuplet uuid
        rv = self.app.post('/preddone/ad_0',
                           data=json.dumps({"status": "done"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)
        # wrong key in request
        rv = self.app.post('/preddone/id_0',
                           data=json.dumps({"sttys": "oups"}),
                           content_type='application/json',
                           headers=headers)
        self.assertEqual(rv.status_code, 400)

    def test_get_filtered_document(self):
        learnuplets = generate_list_learnuplets(10)
        self.db.learnuplet.insert_many(learnuplets)
        # should be ok
        rv = self.app.get('/learnuplet?uuid=id_0',
                           content_type='application/json',
                          headers=headers)
        self.assertEqual(rv.status_code, 200)
        # wrong url
        rv = self.app.get('/learnupleto?uuid=id_0',
                           content_type='application/json',
                          headers=headers)
        self.assertEqual(rv.status_code, 404)
        # wrong filter returns nothing
        rv = self.app.get('/learnuplet?uuido=id_0',
                           content_type='application/json',
                          headers=headers)
        self.assertFalse(json.loads(rv.get_data(as_text=True))["learnuplets"])


if __name__ == '__main__':
    unittest.main()
