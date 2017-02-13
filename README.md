# Orchestrator

A RESTful API with Flask (and [Flask-PyMongo](https://flask-pymongo.readthedocs.io/en/latest/)) for the Orchestrator.

## Getting started

Requirements:
- [MongoDB](https://www.mongodb.com/download-center)
- Python3
- If you want: virtualenv and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) 

Make sure Python3 and MongoDB are installed.

Clone the repository, create a virtual environment with Python3, and instal pip packages:
```
git clone https://github.com/DeepSeeOrg/orchestrator.git
cd orchestrator
mkvirtualenv --python=/usr/bin/python3 orchestrator
setvirtualenvproject
pip install -r requirements.txt
```

## Usage

Start MongoDB: `sudo service mongod start` on Linux and `mongod` on OSX.
Launch the app: `python api.py`

Interact with the api:
- GET example: `curl http://127.0.0.1:5000/problem` 
- POST example: `curl http://127.0.0.1:5000/problem -d '{"uuid": "fc896fb1", "workflow": "ac432fx9"}' -X POST -H "Content-type: application/json"`
