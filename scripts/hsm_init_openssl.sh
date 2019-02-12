#!/bin/bash

# this is no longer used - only included for reference

NUM_OF_KEYS=5
NUM_OF_SIGS=3

multisig="5$(printf '%x' ${NUM_OF_SIGS})"

for ((i=1; i<=NUM_OF_KEYS; i++)); do
    echo "Key generation $i"

    priv_file="hsm_priv_$i.pem"
    pub_file="hsm_pub_$i.pem"

    # priv key
    openssl ecparam -name secp256k1 -genkey -out $priv_file -engine primus
    # pub key
    openssl ec -in $priv_file -pubout -out $pub_file -engine primus
    # pub key in text format
    openssl ec -in $pub_file -text -pubin -conv_form compressed -engine primus > temp_pub

    # extract pub bytes only
    multisig+="21"
    multisig+="$(grep '[a-f0-9]\{2\}[:]\{1\}' temp_pub | tr -d [:space:] | sed s/://g | sed '$a\')"

done

multisig+="5$(printf '%x' ${NUM_OF_KEYS})ae"

echo "Multisig: $multisig"
