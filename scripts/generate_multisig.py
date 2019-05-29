#!/usr/bin/env python3
import sys
from federation.multisig import MultiSig
from federation.test_framework import util, script

if len(sys.argv) < 3:
    raise ValueError("Incorrect number of arguments - Specify number of sigs and nodes")

num_of_sigs = int(sys.argv[1])
num_of_nodes = int(sys.argv[2])

if len(sys.argv) == 4:
    wif_prefix = int(sys.argv[3])
    multisig = MultiSig(num_of_nodes, num_of_sigs, compressed=True, wif_prefix=wif_prefix)
else:
    multisig = MultiSig(num_of_nodes, num_of_sigs, compressed=True)

if num_of_nodes == 1 and num_of_sigs == 1:
    key_hash = script.hash160(multisig.keys[0].get_pubkey())
    print("P2PKH-scriptPubkey: 76a914{}88ac".format(util.bytes_to_hex_str(key_hash)))

print(multisig.wifs)
print(multisig.script)
