import random
import numpy as np
import uuid
import api


def create_learnuplet(new_data, sz_batch, test_data, problem_uuid, algo_uuid,
                      start_rank):
    list_new_learnuplets = []
    # permuation of all active data and scattering into batchs
    n_data = len(new_data)
    perm_list = random.sample(range(n_data), n_data)
    batchs_uuid = [list(np.array(new_data)[perm_list[i: i + sz_batch]])
                   for i in range(0, n_data, sz_batch)]
    # for each batch of data create a learnuplet
    for i, train_data in enumerate(batchs_uuid):
        j = i + start_rank
        # TODO create model_uuid from algo uuid + param uuid
        # create an appropriate status for the learnuplet
        if j == start_rank:
            status = 'todo'
        else:
            status = 'waiting'
        new_learnuplet = {"uuid": uuid.uuid4(),
                          "problem": problem_uuid,
                          "model": algo_uuid,
                          "train_data": train_data,
                          "test_data": test_data,
                          "worker": None,
                          "perf": None,
                          "status": status,
                          'rank': j}
        list_new_learnuplets.append(new_learnuplet)
    return list_new_learnuplets


def algo_learnuplet(algo_uuid):
    """
    Create new learnuplet when adding a new algo given its uuid. It looks for
    all active data, ie data associated to the same problem as the algo
    Hypothesis so far: one algo is associated to one model only

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
        sz_batch = problem["size_train_dataset"]
        test_data = problem["test_dataset"]
        problem_uuid = problem["uuid"]
        new_learnuplets = create_learnuplet(
            active_data, sz_batch, test_data, problem_uuid, algo_uuid, 0)
        api.mongo.db.learnuplet.insert_many(new_learnuplets)
        return len(new_learnuplets)
    except ValueError:
        # not enough data to train the model
        return 0


def data_learnuplet(problem_uuid, data_uuids):
    """
    Create new learnuplets with data_uuids (list of data uuid)
    for a problem (given its uuid)

    :param problem_uuid: uuid of the problem
    :param data_uuids: list of data uuid
    :type problem_uuid: uuid
    :type data_uuids: list
    :return: number of created learnuplets
    :rtype: integer
    """
    n = 0  # new learnuplets
    problem = api.mongo.db.problem.find_one({"uuid": problem_uuid})
    sz_batch = problem["size_train_dataset"]
    # create new learnuplets for algo of the same problem
    list_uuid_models = api.mongo.db.learnuplet.find(
        {"problem": problem_uuid}).distinct("model")
    if list_uuid_models:
        sz_batch = problem["size_train_dataset"]
        test_data = problem["test_dataset"]
        for uuid_model in list_uuid_models:
            last_rank = api.mongo.db.learnuplet.find_one(
                {"rank": {"$exists": True}, "model": uuid_model},
                sort=[("rank", -1)])["rank"]
            new_learnuplets = create_learnuplet(data_uuids, sz_batch, test_data,
                                                problem_uuid, uuid_model,
                                                last_rank + 1)
            api.mongo.db.learnuplet.insert_many(new_learnuplets)
            n += len(new_learnuplets)
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
        sort=[("perf", -1)])
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
