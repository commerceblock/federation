#!/usr/bin/env python3
import sys
from federation.multisig import MultiSig
from federation.test_framework import util, script, address

SCRIPT_PREFIX = 97
PUBKEY_PREFIX = 38
WIF_PREFIX = 180

if len(sys.argv) < 3:
    raise ValueError("Incorrect number of arguments - Specify number of sigs and nodes")

num_of_sigs = int(sys.argv[1])
num_of_nodes = int(sys.argv[2])

if len(sys.argv) == 4:
    wif_prefix = int(sys.argv[3])
    multisig = MultiSig(num_of_nodes, num_of_sigs, compressed=True, wif_prefix=wif_prefix)
else:
    multisig = MultiSig(num_of_nodes, num_of_sigs, compressed=True, wif_prefix=WIF_PREFIX)

if num_of_nodes == 1 and num_of_sigs == 1:
    key_hash = script.hash160(multisig.keys[0].get_pubkey())
    print("scriptPubkey: 76a914{}88ac".format(util.bytes_to_hex_str(key_hash)))
    print("address(P2PKH): {}".format(address.key_to_p2pkh_version(multisig.keys[0].get_pubkey(), PUBKEY_PREFIX)))
else:
    key_hash = script.hash160(util.hex_str_to_bytes(multisig.script))
    print("scriptPubkey: a914{}87".format(util.bytes_to_hex_str(key_hash)))
    print("address(P2SH): {}".format(address.script_to_p2sh_version(multisig.script, SCRIPT_PREFIX)))

print("Private keys:\n{}".format(multisig.wifs))
print("Multisig script:\n{}".format(multisig.script))
