#!/bin/bash
set -e

if [ -f /run/secrets/ocean_user ] && [ -f /run/secrets/ocean_pass ]; then
    creds=("--rpcuser=$(cat /run/secrets/ocean_user)" "--rpcpassword=$(cat /run/secrets/ocean_pass)")
elif [ -f /run/secrets/ocean_pass ]; then
    creds=("--rpcpass=$(cat /run/secrets/ocean_pass)")
fi

exec "$@" "${creds[@]}"
