import random
import numpy as np
import uuid
import api

# number of samples required to start a new learning phase
size_batch_update = 2


def algo_learnuplet(algo_uuid):
    """
    Create new learnuplet when adding a new algo given its uuid. It looks for
    all active data, ie data associated to the same problem as the algo
    Hyp: one algo is associated to one model only

    :param algo_uuid: uuid of the algo
    :type algo_uuid: uuid
    :return: number of created learnuplets
    :rtype: integer
    """
    new_algo = api.mongo.db.algo.find_one({"uuid": algo_uuid})
    problem = api.mongo.db.problem.find_one({"uuid": new_algo["problem"]})
    # Find all active data associated to the same problem
    active_data = api.mongo.db.data.find({"problems": problem["uuid"]}).\
        distinct("uuid")
    # Create learnuplet for each fold if enough data exist
    try:
        train_idx_learnuplets = random.sample(range(len(active_data)),
                                              problem["size_train_dataset"])
        train_data = list(np.array(active_data)[train_idx_learnuplets])
        test_data = problem["test_dataset"]
        # Create UUID for learnuplet from random values
        learnuplet_uuid = uuid.uuid4()
        # TODO create model_uuid from algo uuid + param uuid
        new_learnuplet = {"uuid": learnuplet_uuid,
                          "problem": problem["uuid"],
                          "model": algo_uuid,
                          "train_data": train_data,
                          "test_data": test_data,
                          "worker": None,
                          "perf": None,
                          "status": "todo"}
        api.mongo.db.learnuplet.insert_one(new_learnuplet)
        return 1
    except ValueError:
        # not enough data to train the model
        return 0


def data_learnuplet(problem_uuid, data_uuids):
    """
    Fill existing or create new learnuplet with data_uuids (list of data uuid)
    for a problem (given its uuid)

    :param problem_uuid: uuid of the problem
    :param data_uuids: list of data uuid
    :type problem_uuid: uuid
    :type data_uuids: list
    :return: number of created and filled learnuplets
    :rtype: integer
    """
    # fill existing learnuplets corresponding to the same problem
    n = api.mongo.db.learnuplet.update_many(
        {"problem": problem_uuid, "status": "tofill"},
        {"$push": {"train_data": {"$each": data_uuids}}}).modified_count
    # create new learnuplets for algo of the same problem,
    # which were not waiting for update
    uuid_filled_model = api.mongo.db.learnuplet.find(
        {"problem": problem_uuid, "status": "tofill"}).distinct("model")
    new_learnuplet_models = api.mongo.db.learnuplet.find(
        {"problem": problem_uuid, "model" : {"$nin": uuid_filled_model},
         "status": {"$in": ["done"]}}).distinct("model")
    problem = api.mongo.db.problem.find_one({"uuid": problem_uuid})
    if problem and new_learnuplet_models:
        test_data = problem["test_dataset"]
        for new_learnuplet_model in new_learnuplet_models:
            n += 1
            # Create UUID for learnuplet from random values
            learnuplet_uuid = uuid.uuid4()
            # TODO create model_uuid from algo uuid + param uuid
            new_learnuplet = {"uuid": learnuplet_uuid,
                              "problem": problem_uuid,
                              "model": new_learnuplet_model,
                              "train_data": data_uuids,
                              "test_data": test_data,
                              "worker": None,
                              "perf": None,
                              "status": "tofill"}
            api.mongo.db.learnuplet.insert_one(new_learnuplet)
    # if enough data in learnuplet, change status to todo
    api.mongo.db.learnuplet.update_many(
        {"problem": problem_uuid, "status": "tofill",
         "train_data": {"$exists": True},
         "$where": "this.train_data.length > %s" % size_batch_update},
        {"$set": {"status": "todo"}})
    return n


def create_preduplet(new_preduplet):
    """
    Create new preduplet

    :param new_preduplet: Contains the data uuids on which the prediction is
    requested and the associated problem
    :type new_preduplet: dictionary with keys data, problem, timestamp_request
    :return: 1 if creation of a preduplet, 0 if no model found
    """
    learnuplet_best_model = api.mongo.db.learnuplet.find_one(
        {"perf": {"$exists": True}, "problem": new_preduplet["problem"]},
        sort=[("perf", 1)])
    if learnuplet_best_model:
        new_preduplet["uuid"] = uuid.uuid4()
        new_preduplet["model"] = learnuplet_best_model["model"]
        new_preduplet["status"] = "todo"
        new_preduplet["worker"] = None
        new_preduplet["timestamp_done"] = None
        api.mongo.db.preduplet.insert_one(new_preduplet)
        return 1
    else:
        return 0
