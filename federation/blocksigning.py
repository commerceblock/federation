#!/usr/bin/env python3
import sys
import logging
from time import sleep, time
from hashlib import sha256 as _sha256
from .daemon import DaemonThread
from .test_framework.authproxy import JSONRPCException
from .messenger_factory import MessengerFactory
from .connectivity import getoceand
from decimal import Decimal

class BlockSigning(DaemonThread):
    def __init__(self, ocean_conf, messenger_type, nodes, my_id, block_time, in_rate, in_period, in_address, script, signer=None):
        super().__init__()
        self.ocean_conf = ocean_conf
        self.ocean = getoceand(self.ocean_conf)
        self.interval = block_time
        self.total = len(nodes)
        self.my_id = my_id % self.total
        self.logger = logging.getLogger(self.__class__.__name__)

        self.messenger = MessengerFactory.get_messenger(messenger_type, nodes, self.my_id)
        self.signer = signer

        self.rate = in_rate
        self.period = in_period
        self.address = in_address
        self.script = script
        self.inconf = 1
        if in_rate > 0:
            try:
                self.ocean.importprivkey(ocean_conf["reissuanceprivkey"])
            except Exception as e:
                self.logger.error("{}\nFailed to import reissuance private key".format(e))
                sys.exit(1)
            self.riprivk = []
            self.riprivk.append(ocean_conf["reissuanceprivkey"])
            try:
                p2sh = self.ocean.decodescript(script)
            except Exception as e:
                self.logger.error("{}\nFailed to decode reissuance script".format(e))
                sys.exit(1)
            self.p2sh = p2sh["p2sh"]
            self.nsigs = p2sh["reqSigs"]
            self.ocean.importaddress(self.p2sh)
            validate = self.ocean.validateaddress(self.p2sh)
            self.scriptpk = validate["scriptPubKey"]

    def run(self):
        while not self.stop_event.is_set():
            sleep(self.interval - time() % self.interval)
            start_time = int(time())
            step = int(time()) % (self.interval * self.total) / self.interval

            height = self.get_blockcount()
            if height == None:
                self.logger.warning("could not connect to ocean client")
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

                # Inflation only check to see if there are any reissuance transactions to sign
                if self.rate > 0:
                    self.logger.info("node: {} - inflationconf: {}".format(str(self.my_id), str(self.inconf)))
                    if height % self.period == 0 and height != 0:
                        rtxs = self.get_reissuance_txs(height)
                        if len(rtxs) == 0:
                            self.inconf = 1
                        elif len(rtxs) > 0:
                            self.inconf = 0
                    if height != 0 and height % self.period < self.period/2 and "txs" in new_block and self.inconf == 0:
                        sig["txsigs"] = self.get_tx_signatures(new_block["txs"], height, True)
                        sig["id"] = self.my_id
                        if sig["txsigs"] == None and height % self.period == 0:
                            self.logger.warning("could not sign reissuance txs on specified period block")
                        elif sig["txsigs"] != None and height % self.period != 0:
                            self.logger.warning("reissuance txs signed with delay of "+str(height % self.period)+" blocks")

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
                do_submit = 0
                if self.rate > 0:
                    self.logger.info("node: {} - inflationconf: {}".format(str(self.my_id), str(self.inconf)))
                    if height % self.period == 0 and height != 0:
                        block["txs"] = self.get_reissuance_txs(height)
                        if block["txs"] == None:
                            self.logger.warning("could not create reissuance txs")
                            continue
                        if len(block["txs"]) == 0:
                            self.logger.info("no issued assets to inflate")
                            self.inconf = 1
                        elif len(block["txs"]) > 0:
                            self.inconf = 0
                            do_submit = 1
                    #if not reissuance step, in first 1/2 of inflation period and issuance not confirmed, then verify issuance
                    elif self.inconf == 0 and height % self.period > 2 and height % self.period < self.period/2 and height != 0:
                        riconf = self.confirm_reissuance_txs(height)
                        self.logger.info("confirmed: "+str(riconf)+" node "+str(self.my_id))
                        if riconf:
                            self.inconf = 1
                        else:
                            #attempt reissuance again
                            block["txs"] = self.get_reissuance_txs(height)
                            self.inconf = 0
                            do_submit = 1
                            if block["txs"] == None:
                                self.logger.warning("could not create reissuance txs on retry")
                                continue
                    #if reissuance still not confirmed after 30 minutes (period/2) then stop
                    elif self.inconf == 0 and height % self.period > self.period/2:
                        self.logger.error("FATAL: could not issue inflation transactions")
                        self.stop_event.set()

                self.messenger.produce_block(block, height + 1)
                elapsed_time = time() - start_time
                sleep(self.interval / 2 - (elapsed_time if elapsed_time < self.interval / 2 else 0))

                # THEN COLLECT SIGNATURES AND SUBMIT BLOCK
                sigs = self.messenger.consume_sigs(height)
                if len(sigs) == 0: # replace with numOfSigs - 1 ??
                    self.logger.warning("could not get new block sigs")
                    self.messenger.reconnect()
                    continue
                if self.rate > 0:
                    if do_submit == 1:
                        txsigs = [None] * self.total
                        for sig in sigs:
                            txsigs[sig["id"]] = sig["txsigs"]
                        #add sigs for this node
                        mysigs = self.get_tx_signatures(block["txs"], height, False)
                        txsigs[self.my_id] = mysigs
                        signed_txs = self.combine_tx_signatures(block["txs"],txsigs)
                        sent = self.send_reissuance_txs(signed_txs)
                        if sent == None:
                            self.logger.warning("could not send reissuance transactions. node "+str(self.my_id))
                            continue
                blocksigs = []
                for sig in sigs:
                    blocksigs.append(sig["blocksig"])
                self.generate_signed_block(block["blockhex"], blocksigs)

    def get_blockcount(self):
        try:
            return self.ocean.getblockcount()
        except Exception as e:
            self.logger.info("{}\nReconnecting to client...".format(e))
            self.ocean = getoceand(self.ocean_conf)
            return None

    def get_newblockhex(self):
        try:
            return self.ocean.getnewblockhex()
        except Exception as e:
            self.logger.info("{}\nReconnecting to client...".format(e))
            self.ocean = getoceand(self.ocean_conf)
            return None

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

            return self.ocean.signblock(block)
        except Exception as e:
            self.logger.info("{}\nReconnecting to client...".format(e))
            self.ocean = getoceand(self.ocean_conf)
            return None

    def generate_signed_block(self, block, sigs):
        try:
            sigs.append(self.get_blocksig(block))
            blockresult = self.ocean.combineblocksigs(block, sigs)
            signedblock = blockresult["hex"]
            self.ocean.submitblock(signedblock)
            self.logger.info("node {} - submitted block {}".format(self.my_id, signedblock))
        except Exception as e:
            self.logger.info("{}\nReconnecting to client...\nfailed signing".format(e))
            self.ocean = getoceand(self.ocean_conf)
            return None

    def get_reissuance_txs(self, height):
        try:
            token_addr = self.p2sh
            raw_transactions = []
            #retrieve the token report for re-issuing
            utxorep = self.ocean.getutxoassetinfo()
            #get the reissuance tokens from wallet
            unspentlist = self.ocean.listunspent()
            frzhist = self.ocean.getfreezehistory() # get freeze history
            for unspent in unspentlist:
                #re-issuance and policy tokens have issued amount of 10000 as a convention
                if "address" in unspent:
                    if unspent["address"] == token_addr and unspent["amount"] > 9999.0:
                        #find the reissuance details and amounts
                        for entry in utxorep:
                            if entry["token"] == unspent["asset"]:
                                amount_spendable = float(entry["amountspendable"])
                                amount_frozen = float(entry["amountfrozen"])
                                asset = entry["asset"]
                                entropy = entry["entropy"]
                                break
                        #the spendable amount needs to be inflated over a period of 1 hour
                        total_reissue = amount_spendable*(1.0+float(self.rate))**(1.0/(24*365))-amount_spendable
                        #check to see if there are any assets unfrozenx in the last interval
                        amount_unfrozen = 0.0
                        for frzout in frzhist:
                            if frzout["asset"] == asset:
                                if frzout["end"] != 0 and frzout["end"] > height - self.period:
                                    backdate = height - frzout["start"]
                                    elapsed_interval = backdate // self.period
                                    self.logger.info("elapsed_interval: "+str(elapsed_interval))
                                    amount_unfrozen = float(frzout["value"])
                                    total_reissue += amount_unfrozen*(1.0+float(self.rate))**(elapsed_interval/(24*365))-amount_unfrozen
                                    self.logger.info("backdate reissue: "+ str(total_reissue))
                        self.logger.info("Reissue asset "+asset+" by "+str(round(total_reissue,8)))
                        tx = self.ocean.createrawreissuance(self.address,str("%.8f" % round(total_reissue,8)),token_addr,str(unspent["amount"]),unspent["txid"],str(unspent["vout"]),entropy)
                        tx["token"] = unspent["asset"]
                        tx["txid"] = unspent["txid"]
                        tx["vout"] = unspent["vout"]
                        raw_transactions.append(tx)
            return raw_transactions
        except Exception as e:
            self.logger.warning("failed reissuance tx generation: {}".format(e))
            return None

    def confirm_reissuance_txs(self, height):
        try:
            token_addr = self.p2sh
            utxorep = self.ocean.getutxoassetinfo()
            #get the reissuance tokens from wallet
            unspentlist = self.ocean.listunspent()
            numissue = 0
            numnew = 0
            for unspent in unspentlist:
                #re-issuance and policy tokens have issued amount of 10000 as a convention
                if "address" in unspent:
                    if unspent["address"] == token_addr and unspent["amount"] > 9999.0:
                        numissue += 1
                        #check confirmation time - all reissuance tokens should have confirmed in the last 20 blocks (period/3)
                        if unspent["confirmations"] > self.period/3:
                            self.logger.warning("Warning: reissuance failure - unspent reissuance token output: ")
                            self.logger.warning(unspent)
                        else:
                            numnew += 1
            #if no reissuances or all issuances confirmed, return true
            if numissue == 0:
                return True
            elif numnew == numissue:
                return True
            #if there are reissuances, but they are not confirmed, return false
            elif numnew == 0 and numissue > 0:
                return False
            #if only some reissuances have confirmed but other haven't - stop
            else:
                self.logger.error("FATAL: inflation transactions partially confirmed")
                self.stop_event.set()
        except Exception as e:
            self.logger.warning("failed confirmation check: {}".format(e))
            return False

    def check_reissuance(self, transactions, height):
        try:
            mytransactions = self.get_reissuance_txs(height)
            if mytransactions == transactions:
                return True
            else:
                return False
        except Exception as e:
            self.logger.warning("failed reissuance tx checking: {}".format(e))
            return False

    def get_tx_signatures(self, transactions, height, check):
        try:
            signatures = []
            if not check or self.check_reissuance(transactions, height):
                for tx in transactions:
                    inpts = []
                    inpt = {}
                    inpt["txid"] = tx["txid"]
                    inpt["vout"] = tx["vout"]
                    inpt["scriptPubKey"] = self.scriptpk
                    inpt["redeemScript"] = self.script
                    inpts.append(inpt)
                    signedtx = self.ocean.signrawtransaction(tx["hex"],inpts,self.riprivk)
                    sig = ""
                    scriptsig = signedtx["errors"][0]["scriptSig"]
                    ln = int(scriptsig[2:4],16)
                    if ln > 0: sig = scriptsig[2:4] + scriptsig[4:4+2*ln]
                    signatures.append(sig)
            else:
                self.logger.warning("reissuance tx error, node: {}".format(self.my_id))
            return signatures
        except Exception as e:
            self.logger.warning("failed reissuance tx signing: {}".format(e))
            return None

    def int_to_pushdata(self,x):
        x = int(x)
        if x < 253:
            return "{:02x}".format(x)
        else:
            le = "{:04x}".format(x)
            be = "".join([le[x:x+2] for x in range(0,len(le),2)][::-1])
            return "fd"+be

    def combine_tx_signatures(self, transactions, signatures):
        try:
            itr_tx = 0
            for tx in transactions:
                mtx_p = tx["hex"][0:84]
                mtx_s = tx["hex"][86:]
                sigs = []
                #for each tx, get the signatures
                for itr in range(len(signatures)):
                    try:
                        sig = signatures[itr][itr_tx]
                        sigs.append(sig)
                        if len(sigs) == self.nsigs: break
                    except:
                        self.logger.warning("missing node {} signatures".format(itr))
                scriptsig = "00"
                if len(sigs) != self.nsigs:
                    self.logger.warning("error: insufficient sigs for tx {}".format(itr_tx))
                else:
                    #concatenate sigs
                    for s in sigs:
                        scriptsig += s
                    #add the redeem script
                    rsln = len(self.script)//2
                    lnh = hex(rsln)
                    scriptsig += "4c" + lnh[2:] + self.script
                sslh = self.int_to_pushdata(len(scriptsig)//2)
                tx["hex"] = mtx_p + sslh + scriptsig + mtx_s
                itr_tx += 1
            return transactions
        except Exception as e:
            self.logger.warning("failed signature combination: {}".format(e))
            return None

    def send_reissuance_txs(self, transactions):
        txids = []
        try:
            for tx in transactions:
                txid = self.ocean.sendrawtransaction(tx["hex"])
                txids.append(txid)
            return txids
        except Exception as e:
            self.logger.warning("failed tx sending: {}".format(e))
            return None

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
