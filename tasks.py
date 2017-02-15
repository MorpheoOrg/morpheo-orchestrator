import api


# number of samples required to start a new learning phase
size_batch = 2


def algo_learnuplet(algo_uuid):
    """
    Create new learnuplet when adding a new algo given its uuid. It looks for
    all active data, ie data associated to the same problem as the algo
    Hyp: one algo is associated to one model only
    """
    new_algo = api.mongo.db.algo.find_one({"uuid": algo_uuid})
    problem = api.mongo.db.problem.find_one({"uuid": new_algo["problem"]})
    if problem and new_algo:
        # Find all active data associated to the same problem
        active_data = api.mongo.db.data.find({"problems": problem["uuid"]}).\
            distinct("uuid")
        # Create learnuplet for each size batch samples
        nb_learnuplet = len(active_data) // size_batch
        if len(active_data) % size_batch > 0:
            nb_learnuplet +=  1
        data_learnuplets = [active_data[size_batch * i:size_batch * (i + 1)]
                            for i in range(0, nb_learnuplet)]
        for data in data_learnuplets:
            if len(data) < size_batch:
                status = "tofill"
            else:
                status = "todo"
            new_learnuplet = {"problem": problem["uuid"],
                              "model": algo_uuid,
                              "data": data,
                              "worker": None,
                              "perf": None,
                              "status": status}
            api.mongo.db.learnuplet.insert_one(new_learnuplet)
        return "New learnuplet(s) successfully created"
    else:
        return "Problem finding out the algo or the associated problem"
