'''
Models: information of the mongodb collections.
It is just to help understanding.
===============================================

from api import db  # to be defined in api...


class Problem(db.document):
    uuid = db.UUIDField()
    workflow = db.UUIDField()
    timestamp_upload = db.DateTimeField()
    test_dataset = db.ListField(db.UUIDField())
    size_train_dataset = db.IntegerField()


class Poster(db.document):
    uuid = db.UUIDField()
    tokens = db.IntegerField()


class Model(db.document):
    uuid = db.UUIDField()
    active = db.StringField(max_length=10)
    problem = db.UUIDField()
    timestamp_upload = db.DateTimeField()
    poster = db.UUIDField()


class Data(db.document):
    uuid = db.UUIDField()
    problems = db.ListField(db.UUIDField())
    timestamp_upload = db.DateTimeField()
    poster = db.UUIDField()


class Learnuplet(db.Document):
    uuid = db.UUIDField()
    problem = db.UUIDField()
    train_data = db.ListField(db.UUIDField())
    test_data = db.ListField(db.UUIDField())
    algo = db.UUIDField()
    model_start = db.UUIDField()
    model_end = db.UUIDField()
    worker = db.UUIDField()
    perf = db.FloadField()                 # perf on all test dataset
    train_perf = db.ListField(db.FloatField())  # perf on each file
    test_perf = db.ListField(db.FloatField())   # perf on each file
    status = db.StringField(max_length=8)  # todo
                                           # pending, done, failed
    rank = db.IntegerField()
    timestamp_creation = db.DateTimeField()
    timestamp_done = db.DateTimeField()


class Preduplet(db.Document):
    uuid = db.UUIDField()
    problem = db.UUIDField(max_length=50)
    data = db.ListField(db.UUIDField())
    model = db.UUIDField()
    worker = db.UUIDField()
    status = db.StringField(max_length=8)
    timestamp_request = db.DateTimeField()
    timestamp_done = db.DateTimeField()
'''
