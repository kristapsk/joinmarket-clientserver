#!/usr/bin/env python3
import base64
import json
import sys
from optparse import OptionParser
from jmbase import JM_WALLET_NAME_PREFIX
from jmbase.support import EXIT_ARGERROR, IndentedHelpFormatterWithNL, jmprint
from jmclient import add_base_options, BitcoinCoreInterface, check_regtest, \
    get_wallet_path, load_program_config, open_test_wallet_maybe, quit
from jmclient.configure import jm_single
from jmclient.wallet import BaseWallet


description="""Provides Bitcoin Core external signer interface for JoinMarket wallets.
The method is one of the following:
(enumerate)
(getdescriptors)
(signtx)

See <https://github.com/bitcoin/bitcoin/blob/master/doc/external-signer.md> for details.
"""


# Descriptor checksum calculation code taken from
# https://github.com/bitcoin-core/HWI/blob/master/hwilib/descriptor.py

def PolyMod(c: int, val: int) -> int:
    """
    :meta private:
    Function to compute modulo over the polynomial used for descriptor checksums
    From: https://github.com/bitcoin/bitcoin/blob/master/src/script/descriptor.cpp
    """
    c0 = c >> 35
    c = ((c & 0x7ffffffff) << 5) ^ val
    if (c0 & 1):
        c ^= 0xf5dee51989
    if (c0 & 2):
        c ^= 0xa9fdca3312
    if (c0 & 4):
        c ^= 0x1bab10e32d
    if (c0 & 8):
        c ^= 0x3706b1677a
    if (c0 & 16):
        c ^= 0x644d626ffd
    return c

def DescriptorChecksum(desc: str) -> str:
    """
    Compute the checksum for a descriptor
    :param desc: The descriptor string to compute a checksum for
    :return: A checksum
    """
    INPUT_CHARSET = "0123456789()[],'/*abcdefgh@:$%{}IJKLMNOPQRSTUVWXYZ&+-.;<=>?!^_|~ijklmnopqrstuvwxyzABCDEFGH`#\"\\ "
    CHECKSUM_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    c = 1
    cls = 0
    clscount = 0
    for ch in desc:
        pos = INPUT_CHARSET.find(ch)
        if pos == -1:
            return ""
        c = PolyMod(c, pos & 31)
        cls = cls * 3 + (pos >> 5)
        clscount += 1
        if clscount == 3:
            c = PolyMod(c, cls)
            cls = 0
            clscount = 0
    if clscount > 0:
        c = PolyMod(c, cls)
    for j in range(0, 8):
        c = PolyMod(c, 0)
    c ^= 1

    ret = [''] * 8
    for j in range(0, 8):
        ret[j] = CHECKSUM_CHARSET[(c >> (5 * (7 - j))) & 31]
    return ''.join(ret)

def AddChecksum(desc: str) -> str:
    """
    Compute and attach the checksum for a descriptor
    :param desc: The descriptor string to add a checksum to
    :return: Descriptor with checksum
    """
    return desc + "#" + DescriptorChecksum(desc)


def get_descriptor(wallet, mixdepth: int, address_type: int) -> str:
    wallet_type = wallet.get_txtype()
    if wallet_type == "p2pkh":
        function = "pkh"
    elif wallet_type == "p2sh-p2wpkh" or wallet_type == "p2wpkh":
        function = "wpkh"
    else:
        raise Exception("Unsupported wallet type {}".format(wallet_type))
    xpub_key = wallet.get_bip32_pub_export(mixdepth, address_type)
    descriptor = "{}({}/*)".format(function, xpub_key)
    if wallet_type == "p2sh-p2wpkh":
        descriptor = "sh({})".format(descriptor)
    return AddChecksum(descriptor)


def get_fingerprint_from_wallet(wallet_name: str, mixdepth: int) -> str:
    return "{}{}".format(wallet_name.split("-")[2], str(mixdepth).zfill(2))


def get_mixdepth_from_fingerprint(wallet_fingerprint: str) -> int:
    return int(wallet_fingerprint[-2:])


def get_wallet_name_from_fingerprint(wallet_fingerprint: str) -> str:
    return "{}{}".format(JM_WALLET_NAME_PREFIX, wallet_fingerprint[:6])


def main():
    parser = OptionParser(
        usage="usage: %prog [options] wallet method [args...]",
        description=description, formatter=IndentedHelpFormatterWithNL())
    add_base_options(parser)
    parser.add_option("--account",
        type=int,
        action="store",
        dest="account",
        help="")
    parser.add_option("--chain",
        action="store",
        dest="chain",
        help="Select chain to work with.")
    parser.add_option("--fingerprint", "-f",
        action="store",
        dest="wallet_fingerprint",
        help="")
    parser.add_option("--stdin",
        action="store_true",
        dest="commands_and_args_from_stdin",
        help="Enter commands and arguments via stdin.")
    (options, args) = parser.parse_args()
    load_program_config(config_path=options.datadir, bs="no-blockchain")

    if len(args) < 1:
        quit(parser, "Invalid syntax")
    wallet_name = args[0]

    #check_regtest()

    wallet_path = get_wallet_path(wallet_name, None)
    wallet = open_test_wallet_maybe(
        wallet_path, wallet_name, None, read_only=True,
        wallet_password_stdin=options.wallet_password_stdin)

    if options.commands_and_args_from_stdin:
        # This is taken from HWI
        # https://github.com/bitcoin-core/HWI/blob/master/hwilib/_cli.py
        while True:
            try:
                line = input()
                # Exit loop when we see 2 consecutive newlines (i.e. an empty line)
                if line == '':
                    break
                # Split the line and append it to the cli args
                import shlex
                args.extend(shlex.split(line))
            except EOFError:
                # If we see EOF, stop taking input
                break

    if len(args) < 2:
        quit(parser, "Invalid syntax")
    method = args[1]

    if method == "enumerate":
        mixdepths = []
        for i in range(wallet.max_mixdepth + 1):
            mixdepths.append({
                "fingerprint": get_fingerprint_from_wallet(
                    wallet.get_wallet_name(), i),
                "model": "JoinMarket"
            })
        print(json.dumps(mixdepths))

    elif method == "getdescriptors":
        if not options.wallet_fingerprint:
            jmprint("Must provide --fingerprint", "error")
            sys.exit(EXIT_ARGERROR)
        assert(wallet.get_wallet_name() == get_wallet_name_from_fingerprint(
            options.wallet_fingerprint))
        if options.account:
            assert(options.account == 0)
        if options.chain:
            if options.chain == "main":
                options.chain = "mainnet"
            elif options.chain == "test":
                options.chain = "testnet"
            assert(options.chain == wallet.network)
        md = get_mixdepth_from_fingerprint(options.wallet_fingerprint)
        print(json.dumps({
            "receive": [
                get_descriptor(wallet, md, BaseWallet.ADDRESS_TYPE_EXTERNAL)
            ],
            "internal": [
                get_descriptor(wallet, md, BaseWallet.ADDRESS_TYPE_INTERNAL)
            ]
        }))

    elif method == "signtx":
        if len(args) < 3:
            jmprint("Must provide PSBT to sign", "error")
            sys.exit(EXIT_ARGERROR)
        if not options.wallet_fingerprint:
            jmprint("Must provide --fingerprint", "error")
            sys.exit(EXIT_ARGERROR)
        assert(wallet.get_wallet_name() == get_wallet_name_from_fingerprint(
            options.wallet_fingerprint))
        # TODO: limit signing to specific mixdepth
        psbt = args[2]
        signed_psbt_and_signresult, err = wallet.sign_psbt(
            base64.b64decode(psbt.encode("ascii")), with_sign_result=True)
        if err:
            jmprint("Failed to sign PSBT. Error message: {}".format(err),
                "error")
        signresult, signedpsbt = signed_psbt_and_signresult
        print(json.dumps({
            "psbt": signedpsbt
        }))

    else:
        parser.error("Unknown bitcoin-core-signer method: " + method)
        sys.exit(EXIT_ARGERROR)


if __name__ == "__main__":
    main()
