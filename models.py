'''
Models: information of the mongodb collections.
It is just to help understanding.
===============================================

from api import db  # to be defined in api...


class Problem(db.document):
    uuid = db.UUIDField()
    workflow = db.UUIDField()
    timestamp_upload = db.DateTimeField()


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
    problem = db.UUIDField()
    data = db.ListField(db.UUIDField())
    model = db.UUIDField()
    worker = db.UUIDField()
    perf = db.FloadField()
    status = db.StringField(max_length=8)  # tofill, todo,
                                           # pending, done, donup (and updated)


class Preduplet(db.EmbeddedDocument):
    problem = db.UUIDField(max_length=50)
    data = db.ListField(db.UUIDField())
    model = db.UUIDField()
    worker = db.UUIDField()
    status = db.StringField(max_length=8)
    timestamp_request = db.DateTimeField()
    timestamp_done = db.DateTimeField()
'''
