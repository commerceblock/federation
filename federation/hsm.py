#!/usr/bin/env python3
import os
import subprocess
from OpenSSL import crypto
from OpenSSL.crypto import FILETYPE_PEM
from OpenSSL.crypto import load_privatekey
from OpenSSL.crypto import sign
import pkcs11
from pkcs11 import KeyType, ObjectClass, Mechanism, MechanismFlag, Attribute
from pkcs11.util import ec


class HsmPkcs11():
    def __init__(self, key_name):
        # load pkcs11 lib
        self.lib = pkcs11.lib(os.environ['PKCS11_LIB'])
        self.user_pin = os.environ['USER_PIN']
        tokens = self.lib.get_tokens(token_label=os.environ['PKCS11_TOKEN_LABEL'])
        self.token = next(tokens)
        self.key_name = key_name

    def sign(self, msg):
        # connect to hsm via pkcs11 token and pin
        with self.token.open(user_pin=self.user_pin) as session:
            for obj in session.get_objects({Attribute.KEY_TYPE: KeyType.EC,
                                            Attribute.LABEL: self.key_name}):
                if obj.object_class == ObjectClass.PRIVATE_KEY:
                    self.key = obj

                    signature = self.key.sign(msg, mechanism=Mechanism.ECDSA_SHA256)
                    return ec.encode_ecdsa_signature(signature) # get DER encoded

class HsmOpenssl():
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
