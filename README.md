# Federation

The client used by the federation nodes of the Ocean network performing block generation and signing, token inflation, and other functions.

## Instructions
1. `python3 setup.py build && python3 setup.py install`
2. For the demo run `./run_demo` or `python3 -m demo`
3. For the federation run `./run_federation` or `python3 -m federation` and provide the following arguments:
`--rpcconnect $HOST --rpocport $PORT --rpcuser $USER --rpcpass $PASS --id $NODE_ID --msgtype $MSG_TYPE --nodes $NODES_LIST`

Federation arguments:

- NODE_ID: Id of the Ocean node
- DATADIR: Datadir of the Ocean node
- MSG_TYPE: Messenger type used. Possible values: 'kafka', 'zmq' (optional, default='kafka')
- NODES: List of node ip/domain names

Example use:

- zmq: `python3 -m federation --rpconnect 127.0.0.1 --rpcport 18443 --rpcuser user --rpcpass pass --id 1 --msgtype zmq --nodes “node0:1503,node1:1502”`
- kafka: `python3 -m federation --rpconnect 127.0.0.1 --rpcport 18443 --rpcuser user --rpcpass pass --id 1` (check federation.py - defaults to 5 nodes)
