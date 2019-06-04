#!/usr/bin/env python3
import os
import time
import subprocess
import logging
from OpenSSL import crypto
from OpenSSL.crypto import FILETYPE_PEM
from OpenSSL.crypto import load_privatekey
from OpenSSL.crypto import sign
import pkcs11
from pkcs11 import KeyType, ObjectClass, Mechanism, Attribute
from pkcs11.util import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec as eccrypto

# hsm pkcs11 interface
class HsmPkcs11():
    def __init__(self, key_name):
        self.logger = logging.getLogger("BitcoinRPC")

        # load pkcs11 lib
        self.lib = pkcs11.lib(os.environ['PKCS11_LIB'])
        self.user_pin = os.environ['USER_PIN']
        self.token = next(self.lib.get_tokens()) # get any token
        self.key_name = key_name

        # initiate session via pkcs11
        start = time.time()
        self.session = self.token.open(user_pin=self.user_pin)
        self.logger.info("time (connect) {}s".format(time.time() - start))
        start = time.time()

        # get key returns >1 key for some reason
        # key = session.get_key(object_class=ObjectClass.PRIVATE_KEY,
        #                         key_type=KeyType.EC,
        #                         label=self.key_name)

        # get key by iterating through all session objects instead
        iterator = self.session.get_objects({Attribute.KEY_TYPE: KeyType.EC,
                                        Attribute.CLASS: ObjectClass.PRIVATE_KEY,
                                        Attribute.LABEL: self.key_name})
        self.key = next(iterator)
        self.logger.info(self.key)
        self.logger.info("time (get private key) {}s".format(time.time() - start))
        start = time.time()
        _ = next(iterator) # test get_objects() still returns > 1
        iterator._finalize()

        iterator = self.session.get_objects({Attribute.KEY_TYPE: KeyType.EC,
                                        Attribute.CLASS: ObjectClass.PUBLIC_KEY,
                                        Attribute.LABEL: self.key_name})
        pub = next(iterator)
        self.logger.info(pub)
        pubder = ec.encode_ec_public_key(pub)
        self.pubcrypto = serialization.load_der_public_key(pubder, default_backend())
        self.logger.info("time (get public key) {}s".format(time.time() - start))
        _ = next(iterator) # test get_objects() still returns > 1
        iterator._finalize()

    # sign msg with key
    def sign(self, msg):
        start = time.time()
        signature = self.key.sign(msg, mechanism=Mechanism.ECDSA_SHA256)
        self.logger.info("time (sign) {}s".format(time.time() - start))

        self.pubcrypto.verify(ec.encode_ecdsa_signature(signature),
            msg, eccrypto.ECDSA(hashes.SHA256()))

        return ec.encode_ecdsa_signature(signature) # get DER encoded

# hsm openssl interface
class HsmOpenssl():
    def __init__(self, key_name):
        self.key_name = key_name
        with open(key_name) as key_file:
            self.key = key_file.read()

    def sign(self, msg):
        priv_key = load_privatekey(FILETYPE_PEM, self.key)

        sig = sign(priv_key, msg, "sha256")
        self.logger.info("sign\n{}".format(sig.hex()))

    def sign_engine(self, msg):
        f = open('data.txt', 'wb')
        f.write(msg)
        f.close()

        command = 'openssl dgst -sha256 -sign {} -keyform ENGINE -engine primus -out sig.txt data.txt && rm data.txt'.format(self.key_name)
        output = subprocess.check_output(['bash','-c', command])

        with open('sig.txt', 'rb') as sig_file:
            self.logger.info("sign engine\n{}".format(sig_file.read().hex()))
            os.remove('sig.txt')
