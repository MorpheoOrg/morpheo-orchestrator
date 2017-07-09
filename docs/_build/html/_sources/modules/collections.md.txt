# Database Collections


## Collection: Problem

A `problem` contains the following elements:
- `uuid`: a unique identifier of the problem. *db.UUIDField()*.  
- `workflow`: UUID of the associated `problem workflow` stored on storage. *db.UUIDField()*.      
  A `problem workflow` mainly defines what are the **data targets** and the **performance metric** used to evaluate machine learning models. 
  An example of a `problem workflow` is given for sleep stages classification [here](https://github.com/MorpheoOrg/hypnogram-wf).
- `timestamp_upload`: timestamp of the problem creation. *db.DateTimeField()*.  
- `test_dataset`: list of UUIDs of test data, which are not accessible, except by `Compute`to compute performances of submitted algorithms. *db.ListField(db.UUIDField())*.
- `size_train_dataset`: size of mini-batch for each training task. *db.IntegerField()*.

## Collection: Learnuplet

A `learnuplet` defines a learning task. It is constructed by the `Orchestrator` in two cases:
- when new data is uploaded  
- when a new algorithm is uploaded 
It is then used by `Compute` to do the training.

A learnuplet is made of the following elements:
- `uuid`: a unique identifier of the task. *db.UUIDField()*.    
- `problem`: the UUID of the problem associated to the learning task. *db.UUIDField()*.   
- `workflow`: the UUID of the problem workflow associated to the learning task. *db.UUIDField()*.   
- `train_data`: list of train data UUIDs, on which the learning will be done. *db.ListField(db.UUIDField())*.      
- `test_data`: list of test data UUIDs, on which the performance of the algorithm is computed. *db.ListField(db.UUIDField())*.    
- `algo`: UUID of submitted algorithm. *db.UUIDField()*.    
- `model_start`: UUID of model to be trained. If `rank=0`, this UUID is the same as `algo`. *db.UUIDField()*.  
- `model_end`: UUID of the model obtained after training of `model_start`. *db.UUIDField()*.    
- `rank`: rank of the task, which defines the order in which learnuplets must be trained. For more details, see in [Details on the construction of a learnuplet at algorithm upload](#learnuplet_construction_algo) and in [Details on the construction of a learnuplet at data upload](#learnuplet_construction_data).  
- `worker`: UUID of worker which is in charge of the training task defined by this learnuplet. *db.UUIDField()*.    
- `status`: status of the training task. It can be `waiting` if we are waiting for a model training with a lower rank, `todo` if the traiing job can start, `pending` if a worker is currently consuming the task, or `done` if training has been done successfully, or `failed` is trainig has been unsuccesfully done. *db.StringField(max_length=8)*.     
- `perf`: performance on test data. *db.FloadField()*.      
- `test_perf`: dictionary of performances on test data: each element is the performance on one test data file (the keys being the corresponding data uuids). *db.ListField(db.FloatField())*.      
- `train_perf`: dictionary of performances on train data: each element is the performance on one train data file (the keys being the corresponding data uuids). *db.ListField(db.FloatField())*.      
- `training_creation`: timestamp of the learnuplet creation. *db.DateTimeField()*.  
- `training_done`: timestamp of feeback from compute (when updating `status` to `done` or `failed`). *db.DateTimeField()*.  

#### <a name="learnuplet_construction_algo"></a> Details on the construction of a learnuplet at algorithm upload

When uploading a new algorithm, its training is specified in `learnuplets` by the `Orchestrator`.  

For now, they are constructed following these steps:  
1. selection of associated `active data`: for now all data corresponding to the same problem with targets.  
This might change later to lower computational costs.  
2. for each mini-batch containing `size_train_dataset` (parameter fixed for the `problem`), creation of a learnuplet.   
Each learnuplet contains the UUID of the model from which to start the training in `model_start`and UUID where to save the model after training in `model_end`.   
The first learnuplet has `rank=0`, `status=todo` and a specified `model_start`
, and other have incremental values of `rank`, `status=todo` and nothing in `model_start` (filled later). 
+Model from which to start the learning is not defined for learnuplets with `rank=i` at learnuplet creation, but when `performance` of `learnuplet` with `rank=i-1` is registered on the `Orchestrator`. At this moment, the `Orchestrator` looks for the `model_end` of the `learnuplet` with the best performance to choose it as the `model_start` for learnuplet of `rank=i`.


#### <a name="learnuplet_construction_data"></a> Details on the construction of a learnuplet at data upload

When uploading new data, relevant models are updated.  

For now, the construction of corresponding `learnuplets` is made as follows:  
1. selection of relevant models called `active models`: for now all models corresponding to the same problem.  
This might change later to lower computational costs.  
2. for each algorithm: 
  - 2.1 find the model which has the best performance (which is not necessarily the one with the highest rank).
  - 2.2 for each mini-batch containing `size_train_dataset` (parameter fixed for the `problem`), creation of a learnuplet starting from the model found in 2.1.  


## Collection: Algo

An `algo` represents a untrained machine learning model for a given `problem` submitted via `Analytics`, stored in `Storage`, and registered in the `Orchestrator` database. 
An `algo` has the following fields:
- `uuid`: a unique identifier of the algo. *db.UUIDField()*. 
- `problem`: UUID of the associated problem. *db.UUIDField()*.  
- `name`: name of the algo. *db.StringField()*.  
- `timestamp_upload`: timestamp of registration on `Orchestrator`.  *db.DateTimeField()*.  

For details about how to register an `algo`, see the [endpoints documentation](./endpoints.html).

**Note**: For now, there is no field to indicate who submitted the algo, since it is out of scope for phase 1.1.
For phase 1.2, a `Poster` collection might be introduced (with an `uuid` and a `token` fields), and its `uuid` might be added to the `algo` table.  

## Collection: Data

A `data` is submitted via the `Viewer`, stored in `Storage`, and registered in the `Orchestrator` database. It has the following fields: 
- `uuid`: a unique identifier of the data. *db.UUIDField()*. 
- `problem`: list of UUIDs of associated problems (a data can be associated with several problems). *db.ListField(db.UUIDField())*.  
- `timestamp_upload`: timestamp of registration on `Orchestrator`.  *db.DateTimeField()*.  

**Note**: For now, there is no field to indicate who submitted the algo, since it is out of scope for phase 1.1.
For phase 1.2, a `Poster` collection might be introduced (with an `uuid` and a `token` fields), and its `uuid` might be added to the `data` table.  

For details about how to register a `data`, see the [endpoints documentation](./endpoints.html).

## Collection: Preduplet  

A `preduplet` is created in the `Orchestrator` when a prediction is requested. It has the following fields:
- `uuid`: . *db.UUIDField()*  
- `problem`: . *db.UUIDField(max_length=50)*.  
- `workflow`: . *db.UUIDField(max_length=50)*.  
- `data`:  . *db.ListField(db.UUIDField())*.  
- `model`: . *db.UUIDField()*.  
- `worker`:  *db.UUIDField()*.  
- `status`:  *db.StringField(max_length=8)*.  
- `timestamp_request`: *db.DateTimeField()*.  
- `timestamp_done`: *db.DateTimeField()*.  

For details about how to request a prediction, see the [endpoints documentation](./endpoints.html).
