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

NUM_OF_NODES = 5
TIME_TO_SLEEP = 1

time.sleep(TIME_TO_SLEEP)

def getelementsd(datadir, conf, args=""):
    return AuthServiceProxy("http://"+conf["rpcuser"]+":"+conf["rpcpassword"]+"@127.0.0.1:"+conf["rpcport"])

def loadConfig(filename):
    conf = {}
    with open(filename) as f:
        for line in f:
            if len(line) == 0 or line[0] == "#" or len(line.split("=")) != 2:
                continue
            conf[line.split("=")[0]] = line.split("=")[1].strip()
    conf["filename"] = filename
    return conf

def main():
    if len(sys.argv) != 3:
        raise ValueError("Incorrect number of arguments - Specify node id and datadir")

    datadir = str(sys.argv[2])
    conf = loadConfig(datadir + "/elements.conf")
    e = getelementsd(datadir, conf)

    logging.basicConfig(
            format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
            level=logging.INFO
            )

    signing_node = BlockSigning(int(sys.argv[1]), e, NUM_OF_NODES)
    signing_node.start()

    try:
        while 1:
            time.sleep(300)

    except KeyboardInterrupt:
        signing_node.stop()

if __name__ == "__main__":
    main()
