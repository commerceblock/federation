#!/usr/bin/env python3
import os
import traceback
import pkcs11
from pkcs11 import KeyType, ObjectClass, Mechanism, MechanismFlag, Attribute, PKCS11Error
from pkcs11.util import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# load pkcs11 lib
lib = pkcs11.lib(os.environ['PKCS11_LIB'])

tokens = lib.get_tokens()
token = next(tokens) # get any token

try:
    # connect to hsm via pkcs11 token and pin
    with token.open(user_pin=os.environ['USER_PIN'], rw=True) as session:

        # ec curve params
        ecparams = session.create_domain_parameters(
            KeyType.EC, {
                # hardcoded curve name for secp256k1 taken from https://www.flexiprovider.de/CurveOIDs.html
                # asn1crypto python library currently missing the secp256k1 named curve parameters
                Attribute.EC_PARAMS: ec.encode_named_curve_parameters('1.3.132.0.10'),
            }, local=True)

        try:
            pub, priv = ecparams.generate_keypair(store=True,
                                              label="{}".format(os.environ['KEY_LABEL']))
        except Exception as e:
            print("key already exists")
            for obj in session.get_objects({Attribute.KEY_TYPE: KeyType.EC,
                                            Attribute.LABEL: "{}".format(os.environ['KEY_LABEL'])}):
                if obj.object_class == ObjectClass.PUBLIC_KEY:
                    pub = obj

        print("{}".format(pub))
        pubder = ec.encode_ec_public_key(pub)
        pubcrypto = serialization.load_der_public_key(pubder, default_backend())
        print(pubcrypto.public_bytes(serialization.Encoding.X962,
                        serialization.PublicFormat.CompressedPoint).hex())

        # # do uncompressed -> compressed manually
        # # similar result as above
        # point = pub[Attribute.EC_POINT]
        # if point[1] == 0x41 and point[2] == 0x04:
        #     x = int(point[3:35].hex(), 16)
        #     y = int(point[35:].hex(), 16)
        #     multisig += '21'
        #     multisig += ('%02x' % (2+(y&1))) + ('%064x' % x)

except PKCS11Error as e:
    print(traceback.format_exc())
