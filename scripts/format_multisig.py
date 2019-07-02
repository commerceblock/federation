#!/usr/bin/env python3

# format a 3 of 5 multisig script of compressed pubkeys
NUM_OF_SIGS = 3
NUM_OF_KEYS = 5

PUB_1 = "0372c3a1e86f1989ecc1363d11461cc3b0ba4b53f0c71874095a37c81f6aa04448"
PUB_2 = "03fd420c3b22768b4c594051857d2f715c1983ec2ade62f63a3ac5648f741767c5"
PUB_3 = "03b3b56ec6449b07547f0d53aabb1075335d715ac43f1cbb858d7499205590f8d8"
PUB_4 = "03777a75e26cce2d475873923ab4c20b26d76b59908cea6a16076a6405c561a700"
PUB_5 = "03f7af4a248408948bce4f7db33a223a2edd30eb27c22003d36a48dd43f1f31d09"

multisig = "{}21{}21{}21{}21{}21{}{}ae".format(\
    50 + NUM_OF_SIGS,
    PUB_1,PUB_2,PUB_3,PUB_4,PUB_5,
    50 + NUM_OF_KEYS)

print("script: {}".format(multisig))
