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
# UUID should be created by Orchestrator. TODO define from what and how
# data: uuid can be one element or a list, in this case all element have same
# problems
post_document = {
    'problem': ['uuid', 'workflow', 'test_dataset', 'size_train_dataset'],
    'algo': ['uuid', 'problem'],
    'data': ['uuid', 'problems'],
    'prediction' : ['data', 'problem']
}
# Existing collections
list_collection = list(post_document.keys()) + ['learnuplet', 'preduplet']


@app.route('/<collection_name>', methods=['GET'])
def get_all_documents(collection_name):
    """
    Get all the document corresponding to the collection_name.
    """
    if collection_name in list_collection:
        collection = mongo.db[collection_name]
        output = [{k: v for k, v in d.items() if k != '_id'}
                  for d in collection.find()]
        return jsonify({'%ss' % collection_name: output}), 200
    else:
        return jsonify({'Error': 'Page does not exist'}), 404


@app.route('/<collection_name>', methods=['POST'])
def add_document(collection_name):
    """
    Add document to the collection whose name is collection_name.
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
        inserted_ids = collection.insert_many(new_docs).inserted_ids
        # find back created document(s)
        uuid_new_docs = collection.find({'_id': {"$in": inserted_ids}}).\
            distinct("uuid")
        # create preduplet or learnuplet
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
    Request a prediction on data for a given problem
    User must post the list of data uuids and the problem uuid
    """
    try:
        request_data = request.get_json()
        new_preduplet = {k: request_data[k]
                         for k in post_document['prediction']}
        new_preduplet['timestamp_request'] = int(time.time())
        n_preduplet = tasks.create_preduplet(new_preduplet)
        if n_preduplet:
            return jsonify({'new_preduplets': n_preduplet}), 201
        else:
            return jsonify({'Error': 'no problem or trained model'}), 400
    except KeyError:
        return jsonify({'Error': 'wrong key in posted data'}), 400


if __name__ == '__main__':
    app.run(debug=True)
