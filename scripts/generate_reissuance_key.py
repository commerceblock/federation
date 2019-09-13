#!/usr/bin/env python3
import sys
import codecs
import os
import hashlib
import random
import time
from federation.test_framework import util, key, address

SCRIPT_PREFIX = 97
PUBKEY_PREFIX = 38
WIF_PREFIX = 180

if len(sys.argv) < 2:
    raise ValueError("Incorrect number of arguments - Specify the node index")

node_id = int(sys.argv[1])

entropy = str(os.urandom(32)) + str(random.getrandbits(256)) + str(int(time.time()*1000000))
k = key.CECKey()
k.set_compressed(True)
pk_bytes = hashlib.sha256(entropy.encode('utf-8')).digest() + b'\x01'
k.set_secretbytes(pk_bytes)
wif = address.byte_to_base58(pk_bytes, WIF_PREFIX)

key_file = open("node_"+str(node_id)+"_ri_privkey.dat","w")
key_file.write(str(wif))
key_file.close()

pubkey = codecs.encode(k.get_pubkey(), 'hex_codec').decode("utf-8")
key_file = open("node_"+str(node_id)+"_ri_pubkey.dat","w")
key_file.write(pubkey)
key_file.close()
