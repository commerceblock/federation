#!/usr/bin/env python3
import sys
from federation.multisig import MultiSig

if len(sys.argv) < 3:
    raise ValueError("Incorrect number of arguments - Specify number of sigs and nodes")

num_of_sigs = int(sys.argv[1])
num_of_nodes = int(sys.argv[2])

if len(sys.argv) == 4:
    wif_prefix = int(sys.argv[3])
    multisig = MultiSig(num_of_nodes, num_of_sigs, compressed=True, wif_prefix=wif_prefix)
else:
    multisig = MultiSig(num_of_nodes, num_of_sigs, compressed=True)

print(multisig.wifs)
print(multisig.script)
