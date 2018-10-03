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

NODES = [0,1,2]
TIME_TO_SLEEP = 60
BLOCK_TIME = 60

time.sleep(TIME_TO_SLEEP)

def main():
    if len(sys.argv) != 3:
        raise ValueError("Incorrect number of arguments - Specify node id and datadir")

    datadir = str(sys.argv[2])
    conf = loadConfig(datadir + "/elements.conf")

    logging.basicConfig(
            format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
            level=logging.INFO
            )

    signing_node = BlockSigning(conf, 'kafka', NODES, int(sys.argv[1]), BLOCK_TIME)
    signing_node.start()

    try:
        while 1:
            time.sleep(300)

    except KeyboardInterrupt:
        signing_node.stop()

if __name__ == "__main__":
    main()
