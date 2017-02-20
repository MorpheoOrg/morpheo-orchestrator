import numpy as np
from sklearn import model_selection
import api

# number of samples required to start a new learning phase
size_batch_update = 2
# number of folds for the cross-validation
n_cv = 2


def cross_val(n_samples, n_splits=n_cv, test_size=0.1):
    """
    Return train sample indices for each fold using sklearn ShuffleSplit
    This function is to be improved to consider better cross validation
    strategies in order to estimate data contributivity and to check
    if enough data for the problem...

    :param n_samples: number of samples
    :param n_splits: number of splits
    :param test-size: percentage of samples for test dataset
    :type n_samples: integer
    :type n_splits: integer
    :type test_size: number between 0 and 1
    :returns: list of indices lists for learnuplets
    :rtype: list
    """
    cv = model_selection.ShuffleSplit(n_splits=n_splits, test_size=test_size,
                                      random_state=42)
    train_learnuplets = [list(train_idx)
                         for train_idx, test_idx in cv.split(range(n_samples))]
    return train_learnuplets


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
    if len(active_data) > 0:
        train_idx_learnuplets = cross_val(len(active_data))
        data_learnuplets = [list(np.array(active_data)[idx_learnuplet])
                            for idx_learnuplet in train_idx_learnuplets]
        for data in data_learnuplets:
            new_learnuplet = {"problem": problem["uuid"],
                              "model": algo_uuid,
                              "data": data,
                              "worker": None,
                              "perf": None,
                              "status": "todo"}
            api.mongo.db.learnuplet.insert_one(new_learnuplet)
        return len(data_learnuplets)
    else:
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
        {"$push": {"data": {"$each": data_uuids}}}).modified_count
    # create new learnuplets for algo of the same problem,
    # which were not waiting for update
    uuid_filled_model = api.mongo.db.learnuplet.find(
        {"problem": problem_uuid, "status": "tofill"}).distinct("model")
    new_learnuplet_models = api.mongo.db.learnuplet.find(
        {"problem": problem_uuid, "model" : {"$nin": uuid_filled_model},
         "status": {"$in": ["done", "donup"]}}).distinct("model")
    for new_learnuplet_model in new_learnuplet_models:
        n += 1
        new_learnuplet = {"problem": problem_uuid,
                          "model": new_learnuplet_model,
                          "data": data_uuids,
                          "worker": None,
                          "perf": None,
                          "status": "tofill"}
        api.mongo.db.learnuplet.insert_one(new_learnuplet)
    # if enough data in learnuplet, change status to todo
    api.mongo.db.learnuplet.update_many(
        {"problem": problem_uuid, "status": "tofill",
         "data": {"$exists": True},
         "$where": "this.data.length > %s" % size_batch_update},
        {"$set": {"status": "todo"}})
    return n
