import time
import random
import numpy as np
import uuid
import api


def create_learnuplet(new_data, sz_batch, test_data, problem_uuid,
                      algo_uuid, model_uuid_start, start_rank):
    """
    Function used to create learnuplets

    :param new_data: list of data UUIDs on which to do the training
    :param sz_batch: mini-batch size
    :param test_data: list of test data UUIDs
    :param problem_uuid: UUID of the problem
    :param algo_uuid: UUID of the submitted algorithm (before any training)
    :param model_uuid_start: UUID of model from which to start the training\
        (equals algo_uuid if start_rank=0)
    :param start_rank: first rank of newly created learnuplets

    :type new_data: list of UUIDs
    :type sz_batch: integer
    :type test_data: list of UUIDs
    :type problem_uuid: UUID
    :type algo_uuid: UUID
    :type model_uuid_start: UUID
    :type start_rank: integer
    """
    # returns empty list of algo_uuid different from model_uuid_start and rank=0
    if start_rank == 0 and model_uuid_start != algo_uuid:
        return []
    list_new_learnuplets = []
    # permuation of all active data and scattering into batchs
    n_data = len(new_data)
    perm_list = random.sample(range(n_data), n_data)
    batchs_uuid = [list(np.array(new_data)[perm_list[i: i + sz_batch]])
                   for i in range(0, n_data, sz_batch)]
    # for each batch of data create a learnuplet
    for i, train_data in enumerate(batchs_uuid):
        j = i + start_rank
        # TODO create model_uuid_end function of model_uuid_start...
        # for now we only generate random UUID....which has to be modified
        model_uuid_end = uuid.uuid4()
        if j == start_rank:
            status = 'todo'
        else:
            status = 'waiting'
        new_learnuplet = {"uuid": uuid.uuid4(),
                          "problem": problem_uuid,
                          "algo": algo_uuid,
                          "model_start": model_uuid_start,
                          "model_end": model_uuid_end,
                          "train_data": train_data,
                          "test_data": test_data,
                          "worker": None,
                          "perf": None,
                          "status": status,
                          'rank': j,
                          'timestamp_creation': int(time.time()),
                          'timestamp_done': None}
        list_new_learnuplets.append(new_learnuplet)
        model_uuid_start = model_uuid_end
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
        new_learnuplets = create_learnuplet(active_data, sz_batch, test_data,
                                            problem_uuid, algo_uuid,
                                            algo_uuid, 0)
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
    list_uuid_algo = api.mongo.db.learnuplet.find(
        {"problem": problem_uuid}).distinct("algo")
    if list_uuid_algo:
        sz_batch = problem["size_train_dataset"]
        test_data = problem["test_dataset"]
        for uuid_algo in list_uuid_algo:
            last_learnuplet = api.mongo.db.learnuplet.find_one(
                {"rank": {"$exists": True}, "algo": uuid_algo},
                sort=[("rank", -1)])
            last_rank = last_learnuplet["rank"]
            last_model = last_learnuplet["model_end"]
            new_learnuplets = create_learnuplet(data_uuids, sz_batch, test_data,
                                                problem_uuid, uuid_algo,
                                                last_model, last_rank + 1)
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
        new_preduplet["model"] = learnuplet_best_model["model_end"]
        new_preduplet["status"] = "todo"
        new_preduplet["worker"] = None
        new_preduplet["timestamp_done"] = None
        api.mongo.db.preduplet.insert_one(new_preduplet)
        return 1
    else:
        return 0
