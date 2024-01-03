import atexit
import os
import sqlite3
from typing import List, Optional

from jmbase import bintohex, dict_factory, hextobin


class TransactionCache:

    def __init__(self, database: str) -> None:
        self.database_file = database
        if self.database_file != ":memory:":
            with sqlite3.connect(self.database_file) as source_db:
                self.db = sqlite3.connect(":memory:")
                source_db.backup(self.db)
            atexit.register(self._commit)
        else:
            self.db = sqlite3.connect(database)
        self.db.row_factory = dict_factory
        self._create()

    def _create(self) -> None:
        self.db.executescript("""
            BEGIN;
            CREATE TABLE IF NOT EXISTS transactions (
                txid BLOB NOT NULL,
                blockheight INTEGER NOT NULL,
                blockhash BLOB NOT NULL,
                blocktime INTEGER NOT NULL,
                tx BLOB NOT NULL,
                PRIMARY KEY (txid)
            );
            CREATE TABLE IF NOT EXISTS tx_our_inputs (
                wallet_id TEXT NOT NULL,
                txid BLOB NOT NULL,
                script TEXT NOT NULL,
                value INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_walletid_txid
                ON tx_our_inputs (wallet_id, txid);
            COMMIT;
        """)

    def _commit(self) -> None:
        self.db.commit()
        os.remove(self.database_file)
        dest_db = sqlite3.connect(self.database_file)
        self.db.backup(dest_db)
        dest_db.commit()

    def get_transaction(self, txid: str) -> Optional[dict]:
        assert isinstance(txid, str)
        tx_db = self.db.cursor()
        res = tx_db.execute(
            "SELECT blockheight, blockhash, blocktime, tx "
            "FROM transactions WHERE txid = ?", [hextobin(txid)])
        row = res.fetchone()
        if row:
            row["txid"] = txid
            row["blockhash"] = bintohex(row["blockhash"])
            row["hex"] = bintohex(row["tx"])
        return row

    def add_transaction(self, txdata: dict) -> None:
        assert "txid" in txdata
        assert isinstance(txdata["txid"], str)
        assert "blockheight" in txdata
        assert isinstance(txdata["blockheight"], int)
        assert "blockhash" in txdata
        assert isinstance(txdata["blockhash"], str)
        assert "blocktime" in txdata
        assert isinstance(txdata["blocktime"], int)
        assert "hex" in txdata
        assert isinstance(txdata["hex"], str)
        self.db.execute(
            "INSERT INTO transactions ("
                "txid, blockheight, blockhash, blocktime, tx) "
            "VALUES (?, ?, ?, ?, ?)", [
                hextobin(txdata["txid"]), txdata["blockheight"],
                hextobin(txdata["blockhash"]), txdata["blocktime"],
                hextobin(txdata["hex"])
            ])

    def get_tx_our_inputs(self, wallet_id: str,
                          txid: str) -> List[dict]:
        assert isinstance(wallet_id, str)
        assert isinstance(txid, str)
        tx_db = self.db.cursor()
        return tx_db.execute(
            "SELECT script, value FROM tx_our_inputs "
            "WHERE wallet_id = ? AND txid = ?",
            [ wallet_id, txid ]).fetchall()

    def add_tx_our_inputs(self, wallet_id: str, txid: str,
                          inputs: List[dict]) -> None:
        assert isinstance(wallet_id, str)
        assert isinstance(txid, str)
        self.db.execute(
            "DELETE FROM tx_our_inputs "
            "WHERE wallet_id = ? AND txid = ?",
            [ wallet_id, hextobin(txid) ])
        for inp in inputs:
            self.db.execute(
                "INSERT INTO tx_our_inputs (wallet_id, txid, script, value) "
                "VALUES (?, ?, ?, ?)",
                [ wallet_id, hextobin(txid), inp['script'], inp['value'] ])
