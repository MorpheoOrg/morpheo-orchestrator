import api


# number of samples required to start a new learning phase
size_batch = 400


def algo_learnuplet(algo_uuid):
    """
    Create new learnuplet when adding a new algo given its uuid. It looks for
    all active data, ie data that can be used for learning the algo.
    Hyp: one algo is associated to one model only
    """
    new_algo = api.mongo.db.algo.find_one({"uuid": algo_uuid})
    problem = api.mongo.db.problem.find_one({"uuid": new_algo["problem"]})
    if problem and new_algo:
        # Find all active data
        active_data = {}
        pb_learnuplets = api.mongo.db.find({"problem": problem["uuid"]})
        for learnuplet in pb_learnuplets:
            active_data = active_data.union(set(learnuplet["data"]))
        if len(active_data) < size_batch:
            status = "tofill"
        else:
            status = "todo"
        new_learnuplet = {"problem": problem["uuid"],
                          "model": algo_uuid,
                          "data": list(active_data),
                          "worker": None,
                          "perf": None,
                          "status": status}
        api.mongo.db.learnuplet(new_learnuplet)
        return "New learnuplet successfully created"
    else:
        return "Problem finding out the algo or the associated problem"
