#!/bin/bash
set -e

if [ -f /run/secrets/ocean_user ] && [ -f /run/secrets/ocean_pass ]; then
    creds=("--rpcuser=$(cat /run/secrets/ocean_user)" "--rpcpassword=$(cat /run/secrets/ocean_pass)")
elif [ -f /run/secrets/ocean_pass ] && [ -f /run/secrets/reissuance_priv_key ]; then
    creds=("--rpcpassword=$(cat /run/secrets/ocean_pass)" "--reissuanceprivkey=$(cat /run/secrets/reissuance_priv_key)")
elif [ -f /run/secrets/ocean_pass ]; then
    creds=("--rpcpassword=$(cat /run/secrets/ocean_pass)")
fi

command="$@ ${creds[@]}"

bash -c "${command}"
