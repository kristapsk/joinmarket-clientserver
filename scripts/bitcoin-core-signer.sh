#!/usr/bin/env bash

if [ "$3" == "" ]; then
    echo "Usage: $(basename "$0") wallet_name wallet_password method [args...]"
    exit 1
fi

wallet_name="$1"
shift
wallet_password="$1"
shift

cd $(dirname "$0")/.. && \
source jmvenv/bin/activate && \
cd scripts && \
(echo "$wallet_password"; cat) | \
    python3 bitcoin-core-signer.py --wallet-password-stdin "$wallet_name" "$@"
