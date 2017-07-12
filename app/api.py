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
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_pymongo import PyMongo
import time
import tasks
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)

if os.environ.get('CORS'):
    CORS(app)

# Link to prod db or create dummy db for tests
# Check the environment variable TESTING
testing = os.environ.get('TESTING', "F")
if testing == "T":
    # link to (actually create) dummy db (destroyed at the end of tests)
    app.config['MONGO_DBNAME'] = 'test_orchestrator'
    app.config['TESTING'] = True
else:
    # link to prod db
    app.config['MONGO_DBNAME'] = 'orchestrator'

mongo_host = os.environ.get('MONGO_HOST', "localhost")
app.config['MONGO_HOST'] = mongo_host
mongo = PyMongo(app)

auth = HTTPBasicAuth()
users = {os.environ.get('USER_AUTH'): os.environ.get('PWD_AUTH')}


@auth.get_password
def get_pw(username):
    if username in users:
        return users.get(username)
    return None

# Compute url to push new task to it (should be removed in phase 1.2)
compute_url = os.environ.get('COMPUTE_URL')

# Document fields to be added
# data: uuid can be one element or a list, in this case all element have same
# problems
post_document = {
    'problem': ['uuid', 'workflow', 'test_dataset', 'size_train_dataset'],
    'algo': ['uuid', 'problem', 'name'],
    'data': ['uuid', 'problems'],
}
# Existing collections
list_collection = list(post_document.keys()) + ['learnuplet', 'preduplet']
# Requirements for other post requests
post_request = {'prediction': ['data', 'problem']}


@app.route('/<collection_name>', methods=['GET'])
@auth.login_required
def get_all_documents(collection_name):
    """
    - (*collection_name*) : **problem**, **algo**, **data**, **learnuplet**,
    or **preduplet**

    Get all the documents corresponding to the (*collection_name*).
    Possible to add filter to your request (e.g. **/learnuplet?uuid=blabla**)

    **Success Response content**:
        - *problems/algos/datas/learnuplets/preduplets*: list of corresponding
        documents
    """
    if collection_name in list_collection:
        collection = mongo.db[collection_name]
        output = [{k: v for k, v in d.items() if k != '_id'}
                  for d in collection.find(request.args)]
        return jsonify({'%ss' % collection_name: output}), 200
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/<collection_name>/<document_uuid>', methods=['GET'])
@auth.login_required
def get_document(collection_name, document_uuid):
    """
    - (*collection_name*) : **problem**, **algo**, **data**, **learnuplet**,
    or **preduplet**
    - (*document_uuid*) :UUID of the requested document

    Get a document of a collection

    **Success Response content**:
        - *problem/algo/data/learnuplet/preduplet*: document elements
    """
    if collection_name in list_collection:
        collection = mongo.db[collection_name]
        d = collection.find_one({"uuid": document_uuid})
        output = {k: v for k, v in d.items() if k != '_id'}
        return jsonify({collection_name: output}), 200
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/problem', methods=['POST'])
@auth.login_required
def add_problem():
    """
    Add a new problem

    **Data to post**:
        - *uuid* : problem UUID
        - *workflow* : workflow UUID
        - *test_dataset* : list of test data UUID
        - *size_train_dataset* : nb of train data per minibatch (integer)

    **Success Response content**:
        - *new_problem*: new problem
    """
    collection = mongo.db['problem']
    try:
        request_data = request.get_json()
        # TODO: validation on fields + check element does not exist
        # TODO: check element exists on Storage
        new_doc = {k: request_data[k] for k in post_document['problem']}
        new_doc['timestamp_upload'] = int(time.time())
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400
    # put doc in db
    inserted_id = collection.insert_one(new_doc).inserted_id
    inserted_doc = collection.find_one({'_id': inserted_id})
    inserted_doc.pop('_id')
    return jsonify({'new_problem': inserted_doc}), 201


@app.route('/algo', methods=['POST'])
@auth.login_required
def add_algo():
    """
    Add a new algorithm

    **Data to post**:
        - *uuid* : algo UUID
        - *name* : algo name
        - *problem* : UUID of associated problem

    **Success Response content**:
        - *new_algo*: new algorithm
        - *new_learnuplets*: number of newly created learnuplets
    """
    n_learnuplets = 0
    collection = mongo.db['algo']
    try:
        request_data = request.get_json()
        # TODO: validation on fields + check element does not exist
        # TODO: check element exists on Storage
        # Check associated problem exists
        problem = mongo.db['problem'].\
            find_one({'uuid': request_data['problem']})
        if not problem:
            return jsonify({'Error': 'non-existing related problem'}), 400
        new_doc = {k: request_data[k] for k in post_document['algo']}
        new_doc['timestamp_upload'] = int(time.time())
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400
    # put doc in db
    inserted_id = collection.insert_one(new_doc).inserted_id
    inserted_doc = collection.find_one({'_id': inserted_id})
    inserted_doc.pop('_id')
    n_learnuplets += tasks.algo_learnuplet(inserted_doc['uuid'])
    return jsonify({'new_algo': inserted_doc,
                    'new_learnuplets': n_learnuplets}), 201


@app.route('/data', methods=['POST'])
@auth.login_required
def add_data():
    """
    Add data

    **Data to post**:
        - *uuid* : data UUID or list of data UUIDs
        - *problems* : UUID or list of UUID of associated problems

    **Success Response content**:
        - *new_datas*: list of new data
        - *new_learnuplets*: number of newly created learnuplets
    """
    n_learnuplets = 0
    collection = mongo.db['data']
    try:
        request_data = request.get_json()
        timestamp = int(time.time())
        # TODO: validation on fields + check element does not exist
        # TODO: check element exists on Storage
        # Check associated problems exists
        for pb in request_data['problems']:
            problem = mongo.db['problem'].find_one({'uuid': pb})
            if not problem:
                return jsonify({'Error': 'non-existing related problem'}), 400
        new_docs = []
        if type(request_data["uuid"]) is not list:
            list_uuids = [request_data["uuid"]]
        else:
            list_uuids = request_data["uuid"]
        for uuid in list_uuids:
            new_doc = {k: request_data[k] for k in
                       post_document['data'] if k != "uuid"}
            new_doc['uuid'] = uuid
            new_doc['timestamp_upload'] = timestamp
            new_docs.append(new_doc)
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400
    # put docs in db
    inserted_ids = collection.insert_many(new_docs).inserted_ids
    # find back created document(s)
    uuid_new_docs = collection.find({'_id': {"$in": inserted_ids}}).\
        distinct("uuid")
    new_docs = [{k: v for k, v in d.items() if k != '_id'}
                for d in collection.find({'_id': {"$in": inserted_ids}})]
    # create learnuplets
    for pb_uuid in request_data["problems"]:
        n_learnuplets += tasks.data_learnuplet(pb_uuid, uuid_new_docs)
    return jsonify({'new_datas': new_docs,
                    'new_learnuplets': n_learnuplets}), 201


@app.route('/prediction', methods=['POST'])
@auth.login_required
def request_prediction():
    """
    Request a prediction on data for a given problem.

    **Data to post**:
        - *data* : list of UUID on which to apply the prediction
        - *problem* : UUID of the associated problem

    **Success Response content**:
        - *new_preduplets*: number of newly created preduplets
    """
    try:
        request_data = request.get_json()
        new_preduplet = {k: request_data[k]
                         for k in post_request['prediction']}
        new_preduplet['timestamp_request'] = int(time.time())
        n_preduplet = tasks.create_preduplet(new_preduplet)
        if n_preduplet:
            return jsonify({'new_preduplets': n_preduplet}), 201
        else:
            return jsonify({'Error': 'no problem or trained model'}), 400
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400


@app.route('/worker/<uplet_type>/<uplet_uuid>', methods=['POST'])
@auth.login_required
def set_uplet_worker(uplet_type, uplet_uuid):
    """
    - (*uplet_type*) : **learnuplet** or **preduplet**
    - (*uplet_uuid*) : **UUID** of the *learnuplet* or *preduplet*

    Update the worker of a learnuplet or preduplet and change its status to
    pending (only exposed to the Compute).

    **Data to post**:
        - *worker* : worker UUID

    **Success Response content**:
        - *learnuplet/preduplet_worker_set*: uuid of updated learnuplet or
        preduplet
    """
    if uplet_type in ['learnuplet', 'preduplet']:
        try:
            collection = mongo.db[uplet_type]
            request_data = request.get_json()
            updated = collection.update_one(
                {'uuid': uplet_uuid, 'status': 'todo'},
                {'$set': {'status': 'pending',
                          'worker': request_data['worker']}})
            if updated.modified_count == 1:
                return jsonify({'%s_worker_set' % uplet_type: uplet_uuid}), 200
            else:
                return jsonify(
                    {'Error':
                     'worker not set for %s %s. Might be already pending' %
                     (uplet_type, uplet_uuid)}), 400
        except KeyError:
            return jsonify({'Error': 'wrong key in posted data'}), 400
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/learndone/<learnuplet_uuid>', methods=['POST'])
@auth.login_required
def report_perf_learnuplet(learnuplet_uuid):
    """
    - (*learnuplet_uuid*) : **learnuplet UUID**

    Post output of learning, which updates the corresponding learnuplet.
    Modify the model_start of subequent learnuplet if performance increase.
    Only exposed to the Compute.

    **Data to post**:
        - *status* : status of the prediction task: *done* or *failed*
        - If *status = done*, post also:
          - *perf* : performance of the trained model on all test data
          - *train_perf* : list of performances (one for each train data file)
          - *test_perf* : list of performances (one for each test data file)

    **Success Response content**:
        - *updated_learnuplet*: uuid of updated learnuplet
    """
    # TODO: check identity of worker
    try:
        request_data = request.get_json()
        # update status in current learnuplet
        updated_status = mongo.db.learnuplet.update_one(
            {'uuid': learnuplet_uuid},
            {'$set': {'status': request_data["status"]}})
        # update perf in current learnuplet if learning has been done
        if request_data["status"] == 'done':
            updated_perf = mongo.db.learnuplet.update_one(
                {'uuid': learnuplet_uuid},
                {'$set': {'perf': request_data["perf"],
                          'train_perf': request_data["train_perf"],
                          'test_perf': request_data["test_perf"]}})
            if updated_perf.modified_count == 1:
                learnuplet_perf = mongo.db.learnuplet.find_one(
                    {'uuid': learnuplet_uuid})
                # find learnuplet with best performance
                best_learnuplet = mongo.db.learnuplet.find_one(
                    {"perf": {"$exists": True},
                     "algo": learnuplet_perf['algo']},
                    sort=[("perf", -1)])
                # change model start in next learnuplet
                next_model_start = best_learnuplet['model_end']
                next_learnuplet = mongo.db.learnuplet.update_one(
                    {'rank': learnuplet_perf['rank'] + 1,
                     'algo': learnuplet_perf['algo']},
                    {'$set': {'model_start': next_model_start}})
                # push it to compute
                if next_learnuplet.modified_count == 1 and compute_url:
                    new_learnuplet = mongo.db.learnuplet.find_one(
                        {'rank': learnuplet_perf['rank'] + 1,
                         'algo': learnuplet_perf['algo']})
                    new_learnuplet.pop('_id')
                    tasks.post_uplet([new_learnuplet], compute_url, 'learn')
        if updated_status.modified_count == 1:
            # return updated learnupets
            return jsonify({'updated_learnuplet': learnuplet_uuid}), 200
        else:
            return jsonify(
                {'Error': 'no update of learnuplet %s' % learnuplet_uuid}), 400
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400


@app.route('/preddone/<preduplet_uuid>', methods=['POST'])
@auth.login_required
def update_preduplet(preduplet_uuid):
    """
    - (*preduplet_uuid*) : **preduplet UUID**

    Update status of a preduplet.
    Only exposed to the Compute.

    **Data to post**:
        - *status* : status of the prediction task: *done* or *failed*

    **Success Response content**:
        - *updated_preduplet*: uuid of updated preduplet
    """
    try:
        request_data = request.get_json()
        updated = mongo.db.preduplet.update_one(
            {'uuid': preduplet_uuid},
            {'$set': {'status': request_data['status'],
                      'timestamp_done': int(time.time())}})
        if updated.modified_count == 1:
            return jsonify({'updated_preduplet': preduplet_uuid}), 200
        else:
            return jsonify(
                {'Error': 'no update of preduplet %s' % preduplet_uuid}), 400
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
