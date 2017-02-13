from flask import Flask, jsonify, request
from flask_pymongo import PyMongo


app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'orchestrator'
mongo = PyMongo(app)


# Document fields to be added
# UUID should be created by Orchestrator. TODO define from what and how
post_document = {
    'problem': ['uuid', 'workflow'],
    'algo': ['uuid', 'problem'],
    'data': ['uuid', 'problems'],
}


@app.route('/<collection_name>', methods=['GET'])
def get_all_elements(collection_name):
    collection = mongo.db[collection_name]
    output = [{k: v for k, v in d.items() if k != '_id'}
               for d in collection.find()]
    return jsonify({'%ss' % collection_name : output})


@app.route('/<collection_name>', methods=['POST'])
def add_problem(collection_name):
    collection = mongo.db[collection_name]
    new_document = {k: request.json[k] for k in post_document[collection_name]}
    # TODO: validation on fields
    problem_id = collection.insert(new_document)
    new_problem = collection.find_one({'_id' : problem_id})
    output = {k: new_problem[k] for k in post_document[collection_name]}
    return jsonify({'new_%s' % collection_name : output})


if __name__ == '__main__':
    app.run(debug=True)
