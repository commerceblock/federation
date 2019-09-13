#!/usr/bin/env python3
import logging
import sys

YEAR = 60*60*24*365

class Inflation():
    def __init__(self, total, my_id, ocean, interval, in_rate, in_period, in_address, script, key):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.total = total
        self.my_id = my_id
        self.interval = interval
        self.rate = in_rate
        self.period = in_period
        self.address = in_address
        self.script = script
        self.inconf = 1

        #Check if the node already has the inflationkey before trying to import it
        self.riprivk = []
        self.riprivk.append(key)
        try:
            p2sh = ocean.decodescript(script)
        except Exception as e:
            self.logger.error("{}\nFailed to decode reissuance script".format(e))
            sys.exit(1)
        self.p2sh = p2sh["p2sh"]
        self.nsigs = p2sh["reqSigs"]

        validate = ocean.validateaddress(self.p2sh)
        have_va_addr = bool(validate["ismine"])
        watch_only = bool(validate["iswatchonly"])
        have_va_prvkey = have_va_addr and not watch_only

        rescan_needed = True

        if have_va_prvkey == False:
            try:
                ocean.importprivkey(key,"privkey",rescan_needed)
            except Exception as e:
                self.logger.error("{}\nFailed to import reissuance private key".format(e))
                sys.exit(1)

            #Have just imported the private key so another rescan should be unnecesasary
            rescan_needed=False

        #Check if we still need to import the address given that we have just imported the private key
        validate = ocean.validateaddress(self.p2sh)
        have_va_addr = bool(validate["ismine"])
        if have_va_addr == False:
            ocean.importaddress(self.p2sh,"reissuance",rescan_needed)
            validate = ocean.validateaddress(self.p2sh)

        self.scriptpk = validate["scriptPubKey"]

    def send_txs(self, ocean, height, block, sigs):
        txsigs = [None] * self.total
        for sig in sigs:
            if "id" in sig and "txsigs" in sig:
                txsigs[sig["id"]] = sig["txsigs"]
        # add sigs for this node
        mysigs = self.get_tx_signatures(ocean, block["txs"], height, False)
        txsigs[self.my_id] = mysigs
        signed_txs = self.combine_tx_signatures(block["txs"], txsigs)
        sent = self.send_reissuance_txs(ocean, signed_txs)
        if sent == None:
            self.logger.warning("could not send reissuance transactions. node "+str(self.my_id))
            return False
        return True

    def create_txs(self, ocean, height):
        self.logger.info("node: {} - inflationconf: {}".format(str(self.my_id), str(self.inconf)))
        txs = None
        if height % self.period == 0:
            txs = self.get_reissuance_txs(ocean, height)
            if txs == None:
                self.logger.warning("could not create reissuance txs")
                return None
            if len(txs) == 0:
                self.logger.info("no issued assets to inflate")
                self.inconf = 1
            else:
                self.inconf = 0
        # If not reissuance step, in first 1/2 of inflation period and issuance not confirmed, then verify issuance
        elif self.inconf == 0 and height % self.period > 2 and height % self.period < self.period/2:
            riconf = self.confirm_reissuance_txs(ocean, height)
            self.logger.info("confirmed: "+str(riconf)+" node "+str(self.my_id))
            if riconf:
                self.inconf = 1
            else:
                #attempt reissuance again
                txs = self.get_reissuance_txs(ocean, height)
                self.inconf = 0
                if txs == None:
                    self.logger.warning("could not create reissuance txs on retry")
                    return None
        # If reissuance still not confirmed after 30 minutes (period/2) then stop
        elif self.inconf == 0 and height % self.period > self.period/2:
            raise Exception("FATAL: could not issue inflation transactions")
        return txs

    def get_tx_sigs(self, ocean, height, new_block):
        self.logger.info("node: {} - inflationconf: {}".format(str(self.my_id), str(self.inconf)))
        rtxs = []
        txsigs = None
        if height % self.period == 0:
            rtxs = self.get_reissuance_txs(ocean, height)
            if rtxs == None:
                self.logger.warning("could not get reissuance txs")
            self.inconf = 1 if rtxs != None and len(rtxs) == 0 else 0
        if self.inconf == 0 and "txs" in new_block:
            if height % self.period == 0:
                if rtxs == new_block["txs"]:
                    txsigs = self.get_tx_signatures(ocean, new_block["txs"], height, False)
                if txsigs == None:
                    self.logger.warning("could not sign reissuance txs on specified period block")
            elif height % self.period < self.period/2:
                txsigs = self.get_tx_signatures(ocean, new_block["txs"], height, True)
                if txsigs != None:
                    self.logger.warning("reissuance txs signed with delay of "+str(height % self.period)+" blocks")
        return txsigs

    def get_reissuance_txs(self, ocean, height):
        #check that the reissuance address has been imported, and if not import
        if ocean.getaccount(self.p2sh) != "reissuance":
            ocean.importaddress(self.p2sh,"reissuance")
        try:
            token_addr = self.p2sh
            raw_transactions = []
            #retrieve the token report for re-issuing
            utxorep = ocean.getutxoassetinfo()
            #get the reissuance tokens from wallet
            unspentlist = ocean.listunspent()
            frzhist = ocean.getfreezehistory() # get freeze history
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
                        total_reissue = amount_spendable*(1.0+float(self.rate))**(self.interval*self.period/YEAR)-amount_spendable
                        #check to see if there are any assets unfrozenx in the last interval
                        amount_unfrozen = 0.0
                        for frzout in frzhist:
                            if frzout["asset"] == asset:
                                if frzout["end"] != 0 and frzout["end"] > height - self.period:
                                    backdate = height - frzout["start"]
                                    elapsed_interval = backdate // self.period
                                    self.logger.info("elapsed_interval: "+str(elapsed_interval))
                                    amount_unfrozen = float(frzout["value"])
                                    total_reissue += amount_unfrozen*(1.0+float(self.rate))**(elapsed_interval*self.interval*self.period/YEAR)-amount_unfrozen
                                    self.logger.info("backdate reissue: "+ str(total_reissue))
                        self.logger.info("Reissue asset "+asset+" by "+str(round(total_reissue,8)))
                        if total_reissue == 0.0:
                            continue
                        tx = ocean.createrawreissuance(self.address,str("%.8f" % round(total_reissue,8)),token_addr,str(unspent["amount"]),unspent["txid"],str(unspent["vout"]),entropy)
                        tx["token"] = unspent["asset"]
                        tx["txid"] = unspent["txid"]
                        tx["vout"] = unspent["vout"]
                        raw_transactions.append(tx)
            return raw_transactions
        except Exception as e:
            self.logger.warning("failed reissuance tx generation: {}".format(e))
            return None

    def confirm_reissuance_txs(self, ocean, height):
        isFatal = False
        try:
            token_addr = self.p2sh
            utxorep = ocean.getutxoassetinfo()
            #get the reissuance tokens from wallet
            unspentlist = ocean.listunspent()
            numissue = 0
            numnew = 0
            for unspent in unspentlist:
                #re-issuance and policy tokens have issued amount of 10000 as a convention
                if "address" in unspent:
                    if unspent["address"] == token_addr and unspent["amount"] > 9999.0:
                        numissue += 1
                        # check confirmation time - all reissuance tokens should have
                        # confirmed in the last 20 blocks (period/3)
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
                isFatal = True
        except Exception as e:
            self.logger.warning("failed confirmation check: {}".format(e))
            return False
        finally:
            if isFatal:
                raise Exception("FATAL: inflation transactions partially confirmed")

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

    def get_tx_signatures(self, ocean, transactions, height, check):
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
                    signedtx = ocean.signrawtransaction(tx["hex"],inpts,self.riprivk)
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
                sslh = int_to_pushdata(len(scriptsig)//2)
                tx["hex"] = mtx_p + sslh + scriptsig + mtx_s
                itr_tx += 1
            return transactions
        except Exception as e:
            self.logger.warning("failed signature combination: {}".format(e))
            return None

    def send_reissuance_txs(self, ocean, transactions):
        try:
            txids = []
            for tx in transactions:
                txid = ocean.sendrawtransaction(tx["hex"])
                txids.append(txid)
            return txids
        except Exception as e:
            self.logger.warning("failed tx sending: {}".format(e))
            return None

def int_to_pushdata(x):
    x = int(x)
    if x < 253:
        return "{:02x}".format(x)
    else:
        le = "{:04x}".format(x)
        be = "".join([le[x:x+2] for x in range(0,len(le),2)][::-1])
        return "fd"+be
