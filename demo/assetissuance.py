#!/usr/bin/env python
import threading
import time
import random

ISSUANCE = 10000000
REISSUANCE = 0

class AssetIssuance(threading.Thread):
    def __init__(self, elements, interval):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        self.daemon = True
        self.elements = elements
        self.interval = interval
        issue = self.elements.issueasset(ISSUANCE, REISSUANCE, False)
        self.asset = issue["asset"]
        time.sleep(5)

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            addr = self.elements.getnewaddress()
            time.sleep(2)
            self.elements.sendtoaddress(addr, random.randint(1,10), "", "", False, self.asset)
            time.sleep(2)
            time.sleep(self.interval)

            if self.stop_event.is_set():
                break
