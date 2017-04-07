import os
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
import time
import tasks


app = Flask(__name__)

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
mongo = PyMongo(app)


# Document fields to be added
# data: uuid can be one element or a list, in this case all element have same
# problems
post_document = {
    'problem': ['uuid', 'workflow', 'test_dataset', 'size_train_dataset'],
    'algo': ['uuid', 'problem'],
    'data': ['uuid', 'problems'],
}
# Existing collections
list_collection = list(post_document.keys()) + ['learnuplet', 'preduplet']
# Requirements for other post requests
post_request = {'prediction': ['data', 'problem']}

@app.route('/<collection_name>', methods=['GET'])
def get_all_documents(collection_name):
    """
    - (*collection_name*) : **problem**, **algo**, **data**, **learnuplet**,
    or **preduplet**

    Get all the document corresponding to the (*collection_name*).
    """
    if collection_name in list_collection:
        collection = mongo.db[collection_name]
        output = [{k: v for k, v in d.items() if k != '_id'}
                  for d in collection.find()]
        return jsonify({'%ss' % collection_name: output}), 200
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/<collection_name>/<collection_filter>', methods=['GET'])
def get_filtered_document(collection_name, collection_filter):
    """
    - (*collection_name*) : **problem**, **algo**, **data**, **learnuplet**,
    or **preduplet**
    - (*collection_filter*): **filter_key=value**

    Get document from (*collection_name*) corresponding to filter\
        (*collection_filter*).
    """
    if collection_name in list_collection:
        filter_key = collection_filter.split('=')[0]
        filter_value = collection_filter.split('=')[1]
        collection = mongo.db[collection_name]
        output = [{k: v for k, v in d.items() if k != '_id'}
                  for d in collection.find({filter_key: filter_value})]
        return jsonify({'%ss' % collection_name: output}), 200
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/<collection_name>', methods=['POST'])
def add_document(collection_name):
    """
    Add document to the collection whose name is (*collection_name*):

    ================  ==========================================================
    Collection name   Data to post
    ================  ==========================================================
    *problem*         - *uuid* : problem UUID
                      - *workflow* : workflow UUID
                      - *test_dataset* : list of test data UUID
                      - *size_train_dataset* : nb of train data per minibatch
    *algo*            - *uuid* : algo UUID
                      - *problem* : UUID of associated problem
    *data*            - *uuid* : data UUID or list of data UUIDs
                      - *problems* : UUID or list of UUID of associated problems
    ================  ==========================================================
    """
    if collection_name in post_document.keys():
        n_learnuplets = 0
        collection = mongo.db[collection_name]
        try:
            request_data = request.get_json()
            timestamp = int(time.time())
            # TODO: validation on fields + check element does not exist
            # TODO: check element exists on Storage
            # if upload of multiple elements
            if type(request_data["uuid"]) is list:
                new_docs = []
                for uuid in request_data["uuid"]:
                    new_doc = {k: request_data[k] for k in
                               post_document[collection_name] if k != "uuid"}
                    new_doc['uuid'] = uuid
                    new_doc['timestamp'] = timestamp
                    new_docs.append(new_doc)
            # if upload of one element
            else:
                new_doc = {k: request_data[k]
                           for k in post_document[collection_name]}
                new_doc['timestamp'] = timestamp
                new_docs = [new_doc]
        except KeyError:
            return jsonify({'Error': 'wrong key in posted data'}), 400
        # put docs in db
        inserted_ids = collection.insert_many(new_docs).inserted_ids
        # returns the documents uuids and create learnuplets
        # find back created document(s)
        uuid_new_docs = collection.find({'_id': {"$in": inserted_ids}}).\
            distinct("uuid")
        # create learnuplets
        if collection_name == 'algo':
            for uuid_new_doc in uuid_new_docs:
                n_learnuplets += tasks.algo_learnuplet(uuid_new_doc)
        elif collection_name == 'data':
            for pb_uuid in request_data["problems"]:
                n_learnuplets += tasks.data_learnuplet(pb_uuid, uuid_new_docs)
        return jsonify({'uuid_new_%s' % collection_name: uuid_new_docs,
                        'new_learnuplets': n_learnuplets}), 201
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/prediction', methods=['POST'])
def request_prediction():
    """
    Request a prediction on data for a given problem.

    **Data to post**:
        - *data* : list of UUID on which to apply the prediction
        - *problem* : UUID of the associated problem
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
def set_uplet_worker(uplet_type, uplet_uuid):
    """
    - (*uplet_type*) : **learnuplet** or **preduplet**
    - (*uplet_uuid*) : **UUID** of the *learnuplet* or *preduplet*

    Update the worker of a learnuplet or preduplet and change its status to
    pending (only exposed to the Compute).

    **Data to post**:
        - *worker* : worker UUID
    """
    if uplet_type in ['learnuplet', 'preduplet']:
        try:
            collection = mongo.db[uplet_type]
            request_data = request.get_json()
            updated = collection.update_one(
                {'uuid': uplet_uuid},
                {'$set': {'status': 'pending',
                          'worker': request_data['worker']}})
            if updated.modified_count == 1:
                return jsonify({'%s_worker_set' % uplet_type: uplet_uuid}), 200
            else:
                return jsonify({'Error': 'no worker set for %s %s' %
                                (uplet_type, uplet_uuid)}), 400
        except KeyError:
            return jsonify({'Error': 'wrong key in posted data'}), 400
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/learndone/<learnuplet_uuid>', methods=['POST'])
def report_perf_learnuplet(learnuplet_uuid):
    """
    - (*learnuplet_uuid*) : **learnuplet UUID**

    Post output of learning, which updates the corresponding learnuplet.
    Modify the model_start of subequent learnuplet if performance increase.
    Only exposed to the Compute.

    **Data to post**:
        - *perf* : performance of the trained model on all test data
        - *train_perf* : list of performances (one for each train data file)
        - *test_perf* : list of performances (one for each test data file)
    """
    # TODO: check identity of worker
    try:
        request_data = request.get_json()
        # update performance in current learnuplet
        updated_perf = mongo.db.learnuplet.update_one(
            {'uuid': learnuplet_uuid},
            {'$set': {'status': 'done',
                      'perf': request_data['perf'],
                      'train_perf': request_data['train_perf'],
                      'test_perf': request_data['test_perf']}})
        if updated_perf.modified_count == 1:
            learnuplet_perf = mongo.db.learnuplet.find_one(
                {'uuid': learnuplet_uuid})
            # find learnuplet with best performance
            best_learnuplet = mongo.db.learnuplet.find_one(
                {"perf": {"$exists": True}, "algo": learnuplet_perf['algo']},
                sort=[("perf", -1)])
            # change model start in next learnuplet
            next_model_start = best_learnuplet['model_end']
            mongo.db.learnuplet.update_one(
                {'rank': learnuplet_perf['rank'] + 1,
                 'algo': learnuplet_perf['algo']},
                {'$set': {'model_start': next_model_start}})
            # return updated learnupets
            return jsonify({'updated_learnuplet': learnuplet_uuid}), 200
        else:
            return jsonify(
                {'Error': 'no update of learnuplet %s' % learnuplet_uuid}), 400
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400


@app.route('/preddone/<preduplet_uuid>', methods=['POST'])
def update_preduplet(preduplet_uuid):
    """
    - (*preduplet_uuid*) : **preduplet UUID**

    Update status of a preduplet.
    Only exposed to the Compute.

    **Data to post**:
        - *status* : status of the prediction task: *done* or *failed*
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
    app.run(debug=True)
