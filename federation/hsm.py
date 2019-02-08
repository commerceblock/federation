#!/usr/bin/env python3
import os
import subprocess

from OpenSSL import crypto
from OpenSSL.crypto import FILETYPE_PEM
from OpenSSL.crypto import load_privatekey
from OpenSSL.crypto import sign

class Hsm():
    def __init__(self, key_name):
        self.key_name = key_name
        with open(key_name) as key_file:
            self.key = key_file.read()

    def sign(self, msg):
        priv_key = load_privatekey(FILETYPE_PEM, self.key)

        sig = sign(priv_key, msg, "sha256")
        print("sign\n{}".format(sig.hex()))

    def sign_engine(self, msg):
        f = open('data.txt', 'wb')
        f.write(msg)
        f.close()

        command = 'openssl dgst -sha256 -sign {} -keyform ENGINE -engine primus -out sig.txt data.txt && rm data.txt'.format(self.key_name)
        output = subprocess.check_output(['bash','-c', command])

        with open('sig.txt', 'rb') as sig_file:
            print("sign engine\n{}".format(sig_file.read().hex()))
            os.remove('sig.txt')
