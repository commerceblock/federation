#!/usr/bin/env python3
import os
import random
import sys
import time
import shutil
import logging
import json
import demo.util as util
import argparse
from decimal import *
from pdb import set_trace
from federation.blocksigning import BlockSigning
from demo.multisig import MultiSig
from demo.client import Client

ELEMENTS_PATH = "elementsd"
DEFAULT_ENABLE_LOGGING = False
DEFAULT_GENERATE_KEYS = False
DEFAULT_RETAIN_DAEMONS = False

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

    extra_args =  "{} {} {} {}".format(signblockarg, coinbasearg, issuecontrolarg, coindestarg)

    # INIT THE OCEAN MAIN NODES
    elements_nodes = []
    tmpdir="/tmp/"+''.join(random.choice('0123456789ABCDEF') for i in range(5))
    for i in range(0, num_of_nodes):
        datadir = tmpdir + "/main" + str(i)
        os.makedirs(datadir)
        os.makedirs(datadir + "/terms-and-conditions")

        confdir=os.path.join(os.path.dirname(__file__), "main"+str(i)+"/elements.conf")
        shutil.copyfile(confdir, datadir+"/elements.conf")
        shutil.copyfile(os.path.join(os.path.dirname(__file__), 'latest.txt'), datadir + "/terms-and-conditions/latest.txt")
        mainconf = util.loadConfig(confdir)

        print("Starting node {} with datadir {} and confdir {}".format(i, datadir, confdir))
        e = util.startelementsd(ELEMENTS_PATH, datadir, mainconf, extra_args)
        time.sleep(5)
        elements_nodes.append(e)
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
    explconf = util.loadConfig(os.path.join(os.path.dirname(__file__), 'explorer/elements.conf'))
    ee = util.startelementsd(ELEMENTS_PATH, explorer_datadir, explconf, extra_args)
    time.sleep(5)

    node_signers = []
    for i in range(num_of_nodes):
        node = BlockSigning(i, elements_nodes[i], num_of_nodes, block_time)
        node_signers.append(node)
        node.start()

    client = Client(ELEMENTS_PATH, num_of_clients, extra_args, True, coindestkey)
    client.start()

    try:
        while 1:
            time.sleep(300)

    except KeyboardInterrupt:
        if not args.retain_daemons:
            for node in node_signers:
                node.stop()

            for elements in elements_nodes:
                elements.stop()

            ee.stop()
            client.stop()

            shutil.rmtree(tmpdir)

if __name__ == "__main__":
    main()
