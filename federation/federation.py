#!/usr/bin/env python3
import os
import random
import sys
import shutil
import logging
import json
import time
import argparse
from decimal import *
from pdb import set_trace
from .test_framework.authproxy import AuthServiceProxy, JSONRPCException
from .blocksigning import BlockSigning
from .connectivity import getoceand, loadConfig

NUM_OF_NODES_DEFAULT = 5
MESSENGER_TYPE_DEFAULT = "kafka"
BLOCK_TIME = 60

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rpconnect', required=True, type=str, help="Client RPC host")
    parser.add_argument('--rpcport', required=True, type=str, help="Client RPC port")
    parser.add_argument('--rpcuser', required=True, type=str, help="RPC username for client")
    parser.add_argument('--rpcpassword', required=True, type=str, help="RPC password for client")
    parser.add_argument('--id', required=True, type=int, help="Federation node id")

    parser.add_argument('--msgtype', default=MESSENGER_TYPE_DEFAULT, type=str, help="Messenger type protocol used by federation. 'Kafka' and 'zmq' values supported")
    parser.add_argument('--nodes', default="", type=str, help="Nodes for zmq protocol. Example use 'node0:1503,node1:1502'")

    return parser.parse_args()

def main():
    args = parse_args()

    conf = {}
    conf["rpcuser"] = args.rpcuser
    conf["rpcpassword"] = args.rpcpassword
    conf["rpcport"] = args.rpcport
    conf["rpcconnect"] = args.rpconnect

    node_id = args.id
    msg_type = args.msgtype

    if args.nodes != "":
        # Provide ip:port for zmq protocol
        nodes = args.nodes.split(',')
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
