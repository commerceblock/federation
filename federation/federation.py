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
from .hsm import HsmPkcs11
from .connectivity import getoceand, loadConfig

NUM_OF_NODES_DEFAULT = 5
MESSENGER_TYPE_DEFAULT = "kafka"
BLOCK_TIME = 60
IN_RATE = 0
IN_PERIOD = 0
IN_ADDRESS = ""
SCRIPT = ""
PRVKEY = ""

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rpconnect', required=True, type=str, help="Client RPC host")
    parser.add_argument('--rpcport', required=True, type=str, help="Client RPC port")
    parser.add_argument('--rpcuser', required=True, type=str, help="RPC username for client")
    parser.add_argument('--rpcpassword', required=True, type=str, help="RPC password for client")
    parser.add_argument('--id', required=True, type=int, help="Federation node id")

    parser.add_argument('--msgtype', default=MESSENGER_TYPE_DEFAULT, type=str, help="Messenger type protocol used by federation. 'Kafka' and 'zmq' values supported")
    parser.add_argument('--nodes', default="", type=str, help="Nodes for zmq protocol. Example use 'node0:1503,node1:1502'")

    parser.add_argument('--inflationrate', default=IN_RATE, type=float, help="Inflation rate. Example 0.0101010101")
    parser.add_argument('--inflationperiod', default=IN_PERIOD, type=int, help="Inflation period (in minutes)")
    parser.add_argument('--inflationaddress', default=IN_ADDRESS, type=str, help="Address for inflation payments")
    parser.add_argument('--reissuancescript', default=SCRIPT, type=str, help="Reissuance token script")
    parser.add_argument('--reissuanceprivkey', default=PRVKEY, type=str, help="Reissuance private key")

    parser.add_argument('--hsm', default=False, type=bool, help="Specify if an HSM will be used for signing blocks")
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

    inrate = args.inflationrate
    inprd = args.inflationperiod
    inaddr = args.inflationaddress
    inscript = args.reissuancescript
    ripk = args.reissuanceprivkey
    conf["reissuanceprivkey"] = ripk

    if args.nodes != "":
        # Provide ip:port for zmq protocol
        nodes = args.nodes.split(',')
    else:
        # Maintain old behavior for Kafka
        nodes = ['']*NUM_OF_NODES_DEFAULT

    signer = None
    if args.hsm:
        signer = HsmPkcs11("{}{}".format(os.environ['KEY_LABEL'], node_id))

    logging.basicConfig(
            format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
            level=logging.INFO
            )

    signing_node = BlockSigning(conf, msg_type, nodes, node_id, BLOCK_TIME, inrate, inprd, inaddr, inscript, signer)
    signing_node.start()

    try:
        while 1:
            time.sleep(300)

    except KeyboardInterrupt:
        signing_node.stop()

if __name__ == "__main__":
    main()
