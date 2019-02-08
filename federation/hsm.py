#!/usr/bin/env python3
import os
from OpenSSL import crypto
from OpenSSL.crypto import FILETYPE_PEM
from OpenSSL.crypto import load_privatekey
from OpenSSL.crypto import sign

class Hsm():
    def __init__(self, key_name):
        with open(key_name) as key_file:
            self.key = key_file.read()

    def do(self):
        content = "73902d2a365fff2724e26d975148124268ec6a84991016683817ea2c973b199b"
        content_bytes = bytes.fromhex(content)

        priv_key = load_privatekey(FILETYPE_PEM, self.key)

        sig = sign(priv_key, content_bytes, "sha256")
        print(sig.hex())
