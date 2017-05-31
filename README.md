# Orchestrator
Provide tracability of learning and predictions on Morpheo platform.

A RESTful API with Flask (and [Flask-PyMongo](https://flask-pymongo.readthedocs.io/en/latest/)).

Documentation (with endpoints specification) can be found [here!](https://morpheoorg.github.io/morpheo-orchestrator/)

**Licence:** CECILL 2.1 (compatible with GNU GPL)

## Getting started

Requirements:
- [MongoDB](https://www.mongodb.com/download-center)
- Python3
- If you want: virtualenv and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) 

Make sure Python3 and MongoDB are installed.

Clone the repository, create a virtual environment with Python3, and instal pip packages:
```
git clone https://github.com/DeepSeeOrg/orchestrator.git
cd orchestrator/app
mkvirtualenv --python=/usr/bin/python3 orchestrator
setvirtualenvproject
pip install -r requirements.txt
```

Define two env variables for (temporary) authentication: `USER_AUTH` and `PWD_AUTH`.

Note: If you want to enable CORS, set the environment variable: `CORS=True`

## Usage

Start MongoDB:  
on Linux it is done automatically but you can force it with  
`sudo service mongod start`  
on OSX  
`mongod`

Launch the app: `python api.py`  
To launch the app with gunicorn: `gunicorn --config gunicorn_config.py api:app`

Interact with the api:
- GET example: `curl -u $USER_AUTH:$PWD_AUTH http://0.0.0.0:5000/problem` 
- POST example: `curl -u $USER_AUTH:$PWD_AUTH http://0.0.0.0:5000/problem -d '{"uuid": "fc896fb1", "workflow": "ac432fx9"}' -X POST -H "Content-type: application/json"`

## Run the app using Docker Compose

Requirements:  
- [docker](https://docs.docker.com/) 
- [docker-compose](https://docs.docker.com/compose/) 1.11.2

To build and run the service:
```
docker-compose up --build
```

## Coverage
We use [coverage.py](http://coverage.readthedocs.io/en/latest/index.html).

Run  
`coverage run test_api.py`  
`coverage report -m api.py`  
Without `-m api.py` the coverage report goes to irrelevant depth. We can specify the files to be reported on with `-m file1 file2 ...`

