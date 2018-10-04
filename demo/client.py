#!/usr/bin/env python
import time
import multiprocessing
import random
from federation.connectivity import *
from .assetissuance import AssetIssuance

WAIT_TIME = 60
ISSUANCE_AMOUNT = 100000
REISSUANCE_AMOUNT = 50
REISSUANCE_TOKEN = 1

class Client(multiprocessing.Process):
    def __init__(self, elementsdir, numofclients, args, myfreecoins=False, freecoinkey=""):
        multiprocessing.Process.__init__(self)
        self.daemon = True
        self.stop_event = multiprocessing.Event()
        self.ocean_conf = [None]*numofclients
        self.num_of_clients = numofclients
        self.assets = [None]*numofclients
        self.my_freecoins = myfreecoins
        self.issuers = []
        self.tmpdir="/tmp/"+''.join(random.choice('0123456789ABCDEF') for i in range(5))

        for i in range(0, self.num_of_clients): # spawn elements signing node
            datadir = self.tmpdir + "/client" + str(i)
            os.makedirs(datadir)
            os.makedirs(datadir + "/terms-and-conditions")

            confdir = os.path.join(os.path.dirname(__file__), "client"+str(i)+"/elements.conf")
            shutil.copyfile(confdir, datadir+"/elements.conf")
            shutil.copyfile(os.path.join(os.path.dirname(__file__), 'latest.txt'), datadir + "/terms-and-conditions/latest.txt")
            mainconf = loadConfig(confdir)

            print("Starting node {} with datadir {} and confdir {}".format(i, datadir, confdir))
            e = startelementsd(elementsdir, datadir, mainconf, args)
            self.ocean_conf[i] = ((mainconf, e))
            time.sleep(10)
            if not self.my_freecoins:
                issuer = AssetIssuance(mainconf, WAIT_TIME)
                issuer.start()
                self.issuers.append(issuer)
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
        self.stop_event.set()

    def run(self):
        send_turn = 0
        while not self.stop_event.is_set():
            if self.my_freecoins:
                # get random addr from nodes
                addr = getelementsd(self.ocean_conf[random.randint(0,self.num_of_clients-1)][0]).getnewaddress()
                time.sleep(2)

                # reconnect to avoid any previous failures
                ocean_client = getelementsd(self.ocean_conf[send_turn][0])
                ocean_client.sendtoaddress(addr, random.randint(1,10), "", "", False, self.assets[send_turn])
                time.sleep(2)
                ocean_client.reissueasset(self.assets[send_turn], REISSUANCE_AMOUNT)
                send_turn = (send_turn + 1) % self.num_of_clients

            time.sleep(WAIT_TIME)
            if self.stop_event.is_set():
                break

if __name__ == "__main__":
    path = "../../ocean/src/elementsd"
    c = Client(path)
    c.start()

    try:
        while 1:
            time.sleep(300)

    except KeyboardInterrupt:
        c.stop()
