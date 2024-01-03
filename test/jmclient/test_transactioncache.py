from jmclient import TransactionCache
from jmclient.configure import get_tx_cache_location


def test_transactioncache():
    tx_data = {
        "txid": "0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098",
        "blockheight": 1,
        "blockhash": "00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048",
        "blocktime": 1231469665,
        "hex": "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0704ffff001d0104ffffffff0100f2052a0100000043410496b538e853519c726a2c91e61ec11600ae1390813a627c66fb8be7947be63c52da7589379515d4e0a604f8141781e62294721166bf621e73a82cbf2342c858eeac00000000"
    }
    tx_cache = TransactionCache(get_tx_cache_location())
    assert tx_cache.get_transaction(tx_data["txid"]) is None
    tx_cache.add_transaction(tx_data)
    res = tx_cache.get_transaction(tx_data["txid"])
    assert res is not None
    assert res["txid"] == tx_data["txid"]
    assert res["blockheight"] == tx_data["blockheight"]
    assert res["blockhash"] == tx_data["blockhash"]
    assert res["blocktime"] == tx_data["blocktime"]
    assert res["hex"] == tx_data["hex"]
