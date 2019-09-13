#!/usr/bin/env python3
import sys
import logging
from time import sleep, time
from hashlib import sha256 as _sha256
from .daemon import DaemonThread
from .test_framework.authproxy import JSONRPCException
from .messenger_factory import MessengerFactory
from .connectivity import getoceand
from .inflation import Inflation

BLOCK_TIME_DEFAULT = 60

class BlockSigning(DaemonThread):
    def __init__(self, conf, nodes, in_rate, in_period, in_address, script, signer=None):
        super().__init__()
        self.conf = conf
        self.ocean = getoceand(self.conf)
        self.interval = BLOCK_TIME_DEFAULT if "blocktime" not in conf else conf["blocktime"]
        self.total = len(nodes)
        self.my_id = conf["id"] % self.total
        self.logger = logging.getLogger(self.__class__.__name__)

        self.messenger = MessengerFactory.get_messenger(conf["msgtype"], nodes, self.my_id)
        self.signer = signer
        self.nsigs = conf["nsigs"]

        self.inflation = None
        if in_rate > 0:
            self.inflation = Inflation(self.total, self.my_id, self.ocean, self.interval, in_rate, in_period, in_address, script, conf["reissuanceprivkey"], signer)

    def run(self):
        while not self.stopped():
            sleep(self.interval - time() % self.interval)
            start_time = int(time())
            step = int(time()) % (self.interval * self.total) / self.interval

            height = self.get_blockcount()
            if height == None:
                continue

            if self.my_id != int(step):
                # NOT OUR TURN - GET BLOCK AND SEND SIGNATURE ONLY
                self.logger.info("node {} - consumer".format(self.my_id))

                new_block = None
                while new_block == None:
                    if (time() - start_time) >= (self.interval / 3): # time limit to get block
                        break
                    new_block = self.messenger.consume_block(height)

                if new_block == None:
                    self.logger.warning("could not get latest suggested block")
                    self.messenger.reconnect()
                    continue

                sig = {}
                sig["blocksig"] = self.get_blocksig(new_block["blockhex"])
                if sig["blocksig"] == None:
                    self.logger.warning("could not sign new block")
                    continue

                # Inflation only, check to see if there are any reissuance transactions to sign
                if height > 0 and self.inflation is not None:
                    txsigs = self.inflation.get_tx_sigs(self.ocean, height, new_block)
                    if txsigs is not None:
                        sig["txsigs"] = txsigs
                        sig["id"] = self.my_id

                self.messenger.produce_sig(sig, height + 1)
                elapsed_time = time() - start_time
                sleep(self.interval / 2 - (elapsed_time if elapsed_time < self.interval / 2 else 0))
            else:
                # OUR TURN - FIRST SEND NEW BLOCK HEX
                self.logger.info("blockcount:{}".format(height))
                self.logger.info("node {} - producer".format(self.my_id))

                block = {}
                block["blockhex"] = self.get_newblockhex()
                if block["blockhex"] == None:
                    self.logger.warning("could not generate new block hex")
                    continue

                #if reissuance step, create raw reissuance transactions
                if height > 0 and self.inflation is not None:
                    try:
                        txs = self.inflation.create_txs(self.ocean, height)
                        if txs is not None:
                            block["txs"] = txs
                    except Exception as e:
                        self.logger.error(e)
                        self.stop()

                self.messenger.produce_block(block, height + 1)
                elapsed_time = time() - start_time
                sleep(self.interval / 2 - (elapsed_time if elapsed_time < self.interval / 2 else 0))

                # THEN COLLECT SIGNATURES AND SUBMIT BLOCK
                sigs = self.messenger.consume_sigs(height)
                if len(sigs) < self.nsigs - 1:
                    self.logger.warning("could not get new block sigs")
                    self.messenger.reconnect()
                    continue

                if self.inflation is not None and "txs" in block and block["txs"] is not None:
                    if not self.inflation.send_txs(self.ocean, height, block, sigs):
                        continue

                blocksigs = []
                for sig in sigs:
                    blocksigs.append(sig["blocksig"])
                self.generate_signed_block(block["blockhex"], blocksigs)

    def rpc_retry(self, rpc_func, *args):
        for i in range(5):
            try:
                return rpc_func(*args)
            except Exception as e:
                self.logger.warning("{}\nReconnecting to client...".format(e))
                self.ocean = getoceand(self.conf)
        self.logger.error("Failed reconnecting to client")
        self.stop()

    def get_blockcount(self):
        return self.rpc_retry(self.ocean.getblockcount)

    def get_newblockhex(self):
        return self.rpc_retry(self.ocean.getnewblockhex)

    def get_blocksig(self, block):
        try:
            # hsm block signer
            if self.signer is not None:
                # get block header bytes excluding last byte (Ocean SER_HASH BlockHeader)
                block_header_bytes = get_header(bytes.fromhex(block))
                block_header_for_hash_bytes = block_header_bytes[:len(block_header_bytes)-1]

                # sign the hashed (once not twice) block header bytes
                sig = self.signer.sign(sha256(block_header_for_hash_bytes))

                # turn sig into scriptsig format
                return "00{:02x}{}".format(len(sig), sig.hex())

            return self.rpc_retry(self.ocean.signblock, block)
        except Exception as e:
            self.logger.warning("{}\ncould not get block sig".format(e))
            return None

    def generate_signed_block(self, block, sigs):
        try:
            sigs.append(self.get_blocksig(block))
            blockresult = self.rpc_retry(self.ocean.combineblocksigs, block, sigs)
            signedblock = blockresult["hex"]
            if blockresult["complete"] == True:
                self.rpc_retry(self.ocean.submitblock, signedblock)
                self.logger.info("node {} - submitted block {}".format(self.my_id, signedblock))
            else:
                self.logger.info("node {} - block not submitted".format(self.my_id))
        except Exception as e:
            self.logger.warning("{}\ncould not generate signed block".format(e))

OCEAN_BASE_HEADER_SIZE = 172

def header_hash(block):
    challenge_size = block[OCEAN_BASE_HEADER_SIZE]
    header_without_proof = block[:OCEAN_BASE_HEADER_SIZE+1+challenge_size]
    return double_sha256(header_without_proof)

def get_header(block):
    challenge_size = block[OCEAN_BASE_HEADER_SIZE]
    proof_size = block[OCEAN_BASE_HEADER_SIZE+1+challenge_size]
    return block[:OCEAN_BASE_HEADER_SIZE+1+challenge_size+1+proof_size]

def sha256(x):
    return _sha256(x).digest()

def double_sha256(x):
    return sha256(sha256(x))
