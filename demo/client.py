#!/usr/bin/env python
import time
import multiprocessing
import random
import logging
from federation.connectivity import *
from federation.daemon import DaemonThread

WAIT_TIME = 60
ISSUANCE_AMOUNT = 100000
REISSUANCE_AMOUNT = 50
REISSUANCE_TOKEN = 1

class Client(DaemonThread):
    def __init__(self, oceandir, numofclients, args, script, inflate, freecoinkey=""):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.doinf = inflate
        self.ocean_conf = [None]*numofclients
        self.num_of_clients = numofclients
        self.assets = [None]*numofclients
        self.issuers = []
        self.tmpdir="/tmp/"+''.join(random.choice('0123456789ABCDEF') for i in range(5))
        self.inflate = inflate
        self.script = script

        for i in range(0, self.num_of_clients): # spawn ocean signing node
            datadir = self.tmpdir + "/client" + str(i)
            os.makedirs(datadir)
            os.makedirs(datadir + "/terms-and-conditions/ocean_test")

            confdir = os.path.join(os.path.dirname(__file__), "client"+str(i)+"/ocean.conf")
            shutil.copyfile(confdir, datadir+"/ocean.conf")
            shutil.copyfile(os.path.join(os.path.dirname(__file__), 'latest.txt'), datadir + "/terms-and-conditions/ocean_test/latest.txt")
            mainconf = loadConfig(confdir)

            self.logger.info("Starting node {} with datadir {} and confdir {}".format(i, datadir, confdir))
            e = startoceand(oceandir, datadir, mainconf, args)
            self.ocean_conf[i] = ((mainconf, e))
            time.sleep(10)

            if self.inflate:
                if i == 0:
                    e.importprivkey(freecoinkey)
                    lstun = e.listunspent()
                    for it in lstun:
                        if 'assetlabel' in it:
                            if it['assetlabel'] == 'ISSUANCE':
                                self.issue_txid = it["txid"]
                                self.issue_vout = it["vout"]
                                break
            else:
                e.importprivkey(freecoinkey)
                time.sleep(2)
                issue = e.issueasset(ISSUANCE_AMOUNT, REISSUANCE_TOKEN, False)
                self.assets[i] = issue["asset"]

    def stop(self):
        for ocean in self.ocean_conf:
            ocean[1].stop()
        shutil.rmtree(self.tmpdir)
        for issuer in self.issuers:
            issuer.stop()
        super().stop()

    def run(self):
        send_turn = 0
        send_issuance = 0
        while not self.stopped():
            if not self.inflate:
                # get random addr from nodes
                addr = getoceand(self.ocean_conf[random.randint(0,self.num_of_clients-1)][0]).getnewaddress()
                time.sleep(2)

                # reconnect to avoid any previous failures
                ocean_client = getoceand(self.ocean_conf[send_turn][0])
                ocean_client.sendtoaddress(addr, random.randint(1,10), "", "", False, self.assets[send_turn])
                time.sleep(2)
                ocean_client.reissueasset(self.assets[send_turn], REISSUANCE_AMOUNT)
                send_turn = (send_turn + 1) % self.num_of_clients
            else:
                ocean_client = getoceand(self.ocean_conf[send_turn][0])
                addr = ocean_client.getnewaddress()
                addr2 = ocean_client.getnewaddress()
                p2sh = ocean_client.decodescript(self.script)
                token_addr = p2sh["p2sh"]
                rawissue = ocean_client.createrawissuance(addr,str(10.0),token_addr,'10000',addr2,'210000','1',self.issue_txid,str(self.issue_vout))
                sign_issue = ocean_client.signrawtransaction(rawissue["rawtx"])
                self.issue_txid = ocean_client.sendrawtransaction(sign_issue["hex"])
                self.logger.info("issued 210000 "+str(self.issue_txid))
                issue_decode = ocean_client.decoderawtransaction(sign_issue["hex"])
                for out in issue_decode["vout"]:
                    if out["value"] == 210000.0:
                        self.issue_vout = out["n"]

            time.sleep(WAIT_TIME)

if __name__ == "__main__":
    path = "oceand"
    c = Client(path)
    c.start()

    try:
        while 1:
            if ee.stopped():
                raise Exception("Explorer thread has stopped")
            time.sleep(0.01)
    except Exception as e:
        logger.error(traceback.format_exc())
    except KeyboardInterrupt:
        c.stop()
