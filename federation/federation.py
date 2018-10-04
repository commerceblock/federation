#!/usr/bin/env python3
import os
import random
import sys
import shutil
import logging
import json
import time
from decimal import *
from pdb import set_trace
from .test_framework.authproxy import AuthServiceProxy, JSONRPCException
from .blocksigning import BlockSigning
from .connectivity import getelementsd, loadConfig

NUM_OF_NODES_DEFAULT = 5
MESSENGER_TYPE_DEFAULT = 'kafka'
BLOCK_TIME = 60

def main():
    if len(sys.argv) < 3:
        raise ValueError("Incorrect number of arguments - Specify node id and datadir")

    datadir = str(sys.argv[2])
    conf = loadConfig(datadir + "/elements.conf")

    node_id = int(sys.argv[1])

    if len(sys.argv) > 3:
        msg_type = sys.argv[3]
    else:
        msg_type = MESSENGER_TYPE_DEFAULT

    if len(sys.argv) > 4:
        # Provide ip:port for zmq protocol
        nodes = sys.argv[4].split(',')
    else:
        # Maintain old behavior for Kafka
        nodes = ['']*NUM_OF_NODES_DEFAULT

    logging.basicConfig(
            format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
            level=logging.INFO
            )

    signing_node = BlockSigning(conf, msg_type, nodes, node_id, BLOCK_TIME)
    signing_node.start()

    try:
        while 1:
            time.sleep(300)

    except KeyboardInterrupt:
        signing_node.stop()

if __name__ == "__main__":
    main()
