#!/usr/bin/env python3
import os
import random
import sys
import time
import shutil
import logging
import json
import federation.connectivity as connectivity
import argparse
from decimal import *
from pdb import set_trace
from federation.blocksigning import BlockSigning
from federation.multisig import MultiSig
from .client import Client

ELEMENTS_PATH = "elementsd"
DEFAULT_ENABLE_LOGGING = False
DEFAULT_GENERATE_KEYS = False
DEFAULT_RETAIN_DAEMONS = False
MESSENGER_TYPE = 'zmq'

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--enable-logging', default=DEFAULT_ENABLE_LOGGING, type=bool, help="Enable logging (default: %(default)s)")
    parser.add_argument('-g', '--generate-keys', default=DEFAULT_GENERATE_KEYS, type=bool, help="Generate keys for block generation and free coin issuance (default: %(default)s)")
    parser.add_argument('-r', '--retain-daemons', default=DEFAULT_RETAIN_DAEMONS, type=bool, help="Retain daemons and datadirs when demo stops (default: %(default)s)")
    return parser.parse_args()

def main():
    # GENERATE KEYS AND SINGBLOCK SCRIPT FOR SIGNING OF NEW BLOCKS
    args = parse_args()
    block_time = 60
    num_of_nodes = 3
    num_of_sigs = 2
    num_of_clients = 2
    keys = []
    signblockarg = ""
    coinbasearg = ""
    issuecontrolarg = ""
    coindestarg = ""
    coindestkey = ""
    myfreecoins = True

    if args.generate_keys:  # generate new signing keys and multisig
        if num_of_sigs > num_of_nodes:
                raise ValueError("Num of sigs cannot be larger than num of nodes")
        block_sig = MultiSig(num_of_nodes, num_of_sigs)
        keys = block_sig.wifs
        signblockarg = "-signblockscript={}".format(block_sig.script)
        coinbasearg = "-con_mandatorycoinbase={}".format(block_sig.script)

        issue_sig = MultiSig(1, 1)
        coindestkey = issue_sig.wifs[0]
        coindestarg = "-initialfreecoinsdestination={}".format(issue_sig.script)
        issuecontrolarg = "-issuecontrolscript={}".format(issue_sig.script)

        with open('federation_data.json', 'w') as data_file:
            data = {"keys" : keys, "signblockarg" : signblockarg, "coinbasearg": coinbasearg, "coindestkey" : coindestkey,
                "coindestarg": coindestarg, "issuecontrolarg": issuecontrolarg}
            json.dump(data, data_file)

    else:   # use hardcoded keys and multisig
        with open(os.path.join(os.path.dirname(__file__), 'federation_data.json')) as data_file:
            data = json.load(data_file)
        keys = data["keys"]
        signblockarg = data["signblockarg"]
        coinbasearg = data["coinbasearg"]
        issuecontrolarg = data["issuecontrolarg"]
        coindestarg = data["coindestarg"]
        coindestkey = data["coindestkey"]

    if myfreecoins:
        extra_args =  "{} {} {} {}".format(signblockarg, coinbasearg, issuecontrolarg, coindestarg)
    else:
        extra_args =  "{} {} {}".format(signblockarg, coinbasearg, issuecontrolarg)

    # INIT THE OCEAN MAIN NODES
    ocean_conf = []
    tmpdir="/tmp/"+''.join(random.choice('0123456789ABCDEF') for i in range(5))
    for i in range(0, num_of_nodes):
        datadir = tmpdir + "/main" + str(i)
        os.makedirs(datadir)
        os.makedirs(datadir + "/terms-and-conditions")

        confdir=os.path.join(os.path.dirname(__file__), "main"+str(i)+"/elements.conf")
        shutil.copyfile(confdir, datadir+"/elements.conf")
        shutil.copyfile(os.path.join(os.path.dirname(__file__), 'latest.txt'), datadir + "/terms-and-conditions/latest.txt")
        mainconf = connectivity.loadConfig(confdir)

        print("Starting node {} with datadir {} and confdir {}".format(i, datadir, confdir))
        e = connectivity.startelementsd(ELEMENTS_PATH, datadir, mainconf, extra_args)
        time.sleep(5)
        ocean_conf.append((mainconf, e))
        e.importprivkey(keys[i])
        time.sleep(2)

    if args.enable_logging:
        logging.basicConfig(
                format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
                level=logging.INFO
                )

    # EXPLORER FULL NODE
    explorer_datadir=tmpdir+"/explorer"
    os.makedirs(explorer_datadir)
    os.makedirs(explorer_datadir + "/terms-and-conditions")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), 'explorer/elements.conf'), explorer_datadir+"/elements.conf")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), 'latest.txt'), explorer_datadir + "/terms-and-conditions/latest.txt")
    explconf = connectivity.loadConfig(os.path.join(os.path.dirname(__file__), 'explorer/elements.conf'))
    ee = connectivity.startelementsd(ELEMENTS_PATH, explorer_datadir, explconf, extra_args)
    time.sleep(5)

    # For ZMQ testing host of nodes is required to setup the sockets
    # Sockets are not thread safe though so only 2 nodes will be used,
    # since if there were more multiple nodes will be reading the socket
    # For the demo to work it should not require more than two signatures
    node_ids = ['localhost:%s' % (1500 + i) for i in range(num_of_nodes) ]
    if MESSENGER_TYPE == 'zmq':
        node_ids = node_ids[0:2]

    node_signers = []
    for i in range(len(node_ids)):
        node = BlockSigning(ocean_conf[i][0], MESSENGER_TYPE, node_ids, i, block_time)
        node_signers.append(node)
        node.start()

    client = Client(ELEMENTS_PATH, num_of_clients, extra_args, myfreecoins, coindestkey)
    client.start()

    try:
        while 1:
            time.sleep(300)

    except KeyboardInterrupt:
        if not args.retain_daemons:
            for node in node_signers:
                node.stop()

            for ocean in ocean_conf:
                ocean[1].stop()

            ee.stop()
            client.stop()

            shutil.rmtree(tmpdir)

if __name__ == "__main__":
    main()
