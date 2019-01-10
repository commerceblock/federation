#!/usr/bin/env python3
import threading
import time
import random
from federation.connectivity import getoceand

ISSUANCE = 10000000
REISSUANCE = 0

class AssetIssuance(threading.Thread):
    def __init__(self, ocean_conf, interval):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        self.daemon = True
        self.ocean_conf = ocean_conf
        self.ocean = getoceand(ocean_conf)
        self.interval = interval
        issue = self.ocean.issueasset(ISSUANCE, REISSUANCE, False)
        self.asset = issue["asset"]
        time.sleep(5)

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            self.ocean = getoceand(self.ocean_conf)
            addr = self.ocean.getnewaddress()
            time.sleep(2)
            self.ocean.sendtoaddress(addr, random.randint(1,10), "", "", False, self.asset)
            time.sleep(2)
            time.sleep(self.interval)

            if self.stop_event.is_set():
                break
