#!/usr/bin/env python3
import codecs
import hashlib
from .test_framework import (
    address,
    key,
    util,
)
from .connectivity import *

WIF_PREFIX_TEST = 239

class MultiSig():
    def __init__(self, nodes, sigs, compressed=True, wif_prefix=WIF_PREFIX_TEST):
        self.num_of_nodes = nodes
        self.num_of_sigs = sigs
        self.is_compressed = compressed
        self.wif_prefix = wif_prefix
        self.keys = []
        self.wifs = []
        self.script = ""
        self.initKeys()
        self.generate()

    def initKeys(self):
        for i in range(self.num_of_nodes):
            k = key.CECKey()
            k.set_compressed(self.is_compressed)
            pk_bytes = hashlib.sha256(str(random.getrandbits(256)).encode('utf-8')).digest()
            pk_bytes = pk_bytes + b'\x01' if self.is_compressed else pk_bytes
            k.set_secretbytes(pk_bytes)
            self.keys.append(k)
            self.wifs.append(address.byte_to_base58(pk_bytes, self.wif_prefix))

    def generate(self):
        script = "{}".format(50 + self.num_of_sigs)
        for i in range(self.num_of_nodes):
            k = self.keys[i]
            script += "21"
            script += codecs.encode(k.get_pubkey(), 'hex_codec').decode("utf-8")
        script += "{}".format(50 + self.num_of_nodes) # num keys
        script += "ae" # OP_CHECKMULTISIG
        self.script = script
