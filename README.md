# Federation

The client used by the federation nodes of the Ocean network performing block generation and signing, token inflation, and other functions.

## Instructions
1. `python3 setup.py build && python3 setup.py install`
2. For the demo run `./run_demo` or `python3 -m demo`
3. For the federation run `./run_federation` or `python3 -m federation $NODE_ID $DATADIR $MSG_TYPE $NODES`

Federation arguments:

- NODE_ID: Id of the Ocean node
- DATADIR: Datadir of the Ocean node
- MSG_TYPE: Messenger type used. Possible values: 'kafka', 'zmq' (optional, default='kafka')
- NODES: List of node ip/domain names

Example use:

- zmq: `python3 -m federation 1 /tmp/ABCDE/node0 zmq 'node0:1503,node1:1502'`
- kafka: `python3 -m federation 1 /tmp/ABCDE/node0` (check federation.py - defaults to 5 nodes)
