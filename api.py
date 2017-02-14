import os
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
import time


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
# UUID should be created by Orchestrator.
# TODO define from what and how
post_document = {
    'problem': ['uuid', 'workflow'],
    'algo': ['uuid', 'problem'],
    'data': ['uuid', 'problems'],
}


@app.route('/<collection_name>', methods=['GET'])
def get_all_documents(collection_name):
    collection = mongo.db[collection_name]
    output = [{k: v for k, v in d.items() if k != '_id'}
              for d in collection.find()]
    return jsonify({'%ss' % collection_name: output}), 200


@app.route('/<collection_name>', methods=['POST'])
def add_document(collection_name):
    if collection_name in post_document.keys():
        collection = mongo.db[collection_name]
        try:
            request_data = request.get_json()
            new_document = {k: request_data[k]
                            for k in post_document[collection_name]}
        except KeyError:
            return jsonify({'Error': 'wrong key in posted data'}), 400
        new_document['timestamp_upload'] = int(time.time())
        # TODO: validation on fields
        inserted = collection.insert_one(new_document)
        # return created document
        new_problem = collection.find_one({'_id': inserted.inserted_id})
        output = {k: new_problem[k] for k in post_document[collection_name]}
        return jsonify({'new_%s' % collection_name: output}), 201
    else:
        return jsonify({'Error': 'Page does not exist'}), 400

if __name__ == '__main__':
    app.run(debug=True)
