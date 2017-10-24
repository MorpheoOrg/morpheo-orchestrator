#!/usr/bin/env python3

'''
 Copyright Morpheo Org. 2017

 contact@morpheo.co

 This software is part of the Morpheo project, an open-source machine
 learning platform.

 This software is governed by the CeCILL license, compatible with the
 GNU GPL, under French law and abiding by the rules of distribution of
 free software. You can  use, modify and/ or redistribute the software
 under the terms of the CeCILL license as circulated by CEA, CNRS and
 INRIA at the following URL "http://www.cecill.info".

 As a counterpart to the access to the source code and  rights to copy,
 modify and redistribute granted by the license, users are provided only
 with a limited warranty  and the software's author,  the holder of the
 economic rights,  and the successive licensors  have only  limited
 liability.

 In this respect, the user's attention is drawn to the risks associated
 with loading,  using,  modifying and/or developing or reproducing the
 software by the user in light of its specific status of free software,
 that may mean  that it is complicated to manipulate,  and  that  also
 therefore means  that it is reserved for developers  and  experienced
 professionals having in-depth computer knowledge. Users are therefore
 encouraged to load and test the software's suitability as regards their
 requirements in conditions enabling the security of their systems and/or
 data to be ensured and,  more generally, to use and operate it in the
 same conditions as regards security.

 The fact that you are presently reading this means that you have had
 knowledge of the CeCILL license and that you accept its terms.
'''

import time
import numpy as np
import uuid
import requests
import json
import api


def create_learnuplet(new_data, sz_batch, test_data, problem_uuid,
                      workflow_uuid, algo_uuid, model_uuid_start, start_rank):
    """
    Function used to create learnuplets and push them to Compute

    :param new_data: list of data UUIDs on which to do the training
    :param sz_batch: mini-batch size
    :param test_data: list of test data UUIDs
    :param problem_uuid: UUID of the problem
    :param workflow_uuid: UUID of the workflow
    :param algo_uuid: UUID of the submitted algorithm (before any training)
    :param model_uuid_start: UUID of model from which to start the training\
        (equals algo_uuid if start_rank=0)
    :param start_rank: first rank of newly created learnuplets

    :type new_data: list of UUIDs
    :type sz_batch: integer
    :type test_data: list of UUIDs
    :type problem_uuid: UUID
    :type workflow_uuid: UUID
    :type algo_uuid: UUID
    :type model_uuid_start: UUID
    :type start_rank: integer
    """
    # returns empty list of algo_uuid different from model_uuid_start and rank=0
    if start_rank == 0 and model_uuid_start != algo_uuid:
        return []
    list_new_learnuplets = []
    batchs_uuid = [list(np.array(new_data)[i: i + int(sz_batch)])
                   for i in range(0, len(new_data), int(sz_batch))]
    # for each batch of data create a learnuplet
    for i, train_data in enumerate(batchs_uuid):
        j = i + start_rank
        # TODO create model_uuid_end function of model_uuid_start...
        # for now we only generate random UUID....which has to be modified
        model_uuid_end = str(uuid.uuid4())
        if j == start_rank:
            model_start = model_uuid_start
        else:
            model_start = ''
        new_learnuplet = {"uuid": str(uuid.uuid4()),
                          "problem": problem_uuid,
                          "workflow": workflow_uuid,
                          "algo": algo_uuid,
                          "model_start": model_start,
                          "model_end": model_uuid_end,
                          "train_data": train_data,
                          "test_data": test_data,
                          "worker": None,
                          "perf": None,
                          "train_perf": None,
                          "test_perf": None,
                          "status": 'todo',
                          'rank': j,
                          'timestamp_creation': int(time.time()),
                          'timestamp_done': None}
        # Add learnuplet to db
        api.mongo.db.learnuplet.insert_one(new_learnuplet)
        list_new_learnuplets.append(new_learnuplet)
        model_uuid_start = model_uuid_end
        # Remind learnuplet to be be sent to Compute (which has a model_start)
        worker_url = api.compute_url
        if worker_url and j == start_rank:
            post_uplet([new_learnuplet], worker_url, 'learn')
    return list_new_learnuplets


def post_uplet(list_uplet, worker_url, uplet_prefix):
    """
    post learnuplet/preduplet to a list of workers (Compute)
    :param list_uplet: list of json containing learnuplets/preduplets
    :param worker_url: worker url
    :param uplet_prefix: pred or learn
    :type list_uplet: list
    :type worker_url: url
    :type uplet_prefix: string
    """
    for uplet in list_uplet:
        clean_uplet = {k: v for k, v in uplet.items() if k != '_id'}
        for k, v in clean_uplet.items():
            if type(v) == uuid.UUID:
                clean_uplet[k] = str(v)
        requests.post('%s/%s' % (worker_url, uplet_prefix),
                      data=json.dumps(clean_uplet))


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
    new_learnuplets = []
    if problem:
        active_data = api.mongo.db.data.find({"problems": problem["uuid"]}). \
            sort("timestamp_upload").distinct("uuid")
        test_data = problem["test_dataset"]
        # Filter out test data...
        active_data = list(set(active_data) - set(test_data))
        # Create learnuplet for each fold if enough data exist
        sz_batch = problem["size_train_dataset"]
        problem_uuid = problem["uuid"]
        workflow_uuid = problem["workflow"]
        new_learnuplets = create_learnuplet(
            active_data, sz_batch, test_data, problem_uuid, workflow_uuid,
            algo_uuid, algo_uuid, 0)
    return len(new_learnuplets)


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
        workflow_uuid = problem["workflow"]
        for uuid_algo in list_uuid_algo:
            last_learnuplet = api.mongo.db.learnuplet.find_one(
                {"rank": {"$exists": True}, "algo": uuid_algo},
                sort=[("rank", -1)])
            last_rank = last_learnuplet["rank"]
            # TODO modify. Problem: what if pending models????
            last_model = last_learnuplet["model_end"]
            new_learnuplets = create_learnuplet(
                data_uuids, sz_batch, test_data, problem_uuid,
                workflow_uuid, uuid_algo, last_model, last_rank + 1)
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
    # Find best model
    learnuplet_best_model = api.mongo.db.learnuplet.find_one(
        {"perf": {"$exists": True}, "problem": new_preduplet["problem"]},
        sort=[("perf", -1)])
    # Find associated problem
    problem = api.mongo.db.problem.find_one({"uuid": new_preduplet["problem"]})
    if learnuplet_best_model:
        new_preduplet["uuid"] = str(uuid.uuid4())
        new_preduplet["model"] = learnuplet_best_model["model_end"]
        new_preduplet["status"] = "todo"
        new_preduplet["worker"] = None
        new_preduplet["timestamp_done"] = None
        new_preduplet["workflow"] = problem["workflow"]
        new_preduplet["prediction_storage_uuid"] = None
        api.mongo.db.preduplet.insert_one(new_preduplet)
        # Push the new preduplet to Compute
        worker_url = api.compute_url
        if worker_url:
            post_uplet([new_preduplet], worker_url, 'pred')
        return 1
    else:
        return 0
