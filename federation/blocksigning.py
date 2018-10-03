#!/usr/bin/env python3
from time import sleep, time
from .daemon import DaemonThread
from .test_framework.authproxy import JSONRPCException
from .messenger_factory import MessengerFactory
from .connectivity import getelementsd

class BlockSigning(DaemonThread):
    def __init__(self, ocean_conf, messenger_type, nodes, my_id, block_time):
        super().__init__()
        self.ocean_conf = ocean_conf
        self.ocean = getelementsd(self.ocean_conf)
        self.interval = block_time
        self.total = len(nodes)
        self.my_id = my_id
        self.messenger = MessengerFactory.get_messenger(messenger_type, nodes, my_id)

    def run(self):
        while not self.stop_event.is_set():
            sleep(self.interval - time() % self.interval)
            start_time = int(time())
            step = int(time()) % (self.interval * self.total) / self.interval

            height = self.get_blockcount()
            if height == None:
                print("could not connect to ocean client")
                continue

            if self.my_id != int(step):
                # NOT OUR TURN - GET BLOCK AND SEND SIGNATURE ONLY
                print("node {} - consumer".format(self.my_id))
                sleep(self.interval / 4) # wait for new block

                new_block = self.messenger.consume_block(height)
                if new_block == None:
                    print("could not get latest suggested block")
                    continue

                sig = self.get_blocksig(new_block)
                if sig == None:
                    print("could not sign new block")
                    continue

                self.messenger.produce_sig(sig, height + 1)
                sleep(self.interval / 2 - (time() - start_time))
            else:
                # OUR TURN - FIRST SEND NEW BLOCK HEX
                print("blockcount:{}".format(height))
                print("node {} - producer".format(self.my_id))

                block = self.get_newblockhex()
                if block == None:
                    print("could not generate new block hex")
                    continue
                self.messenger.produce_block(block, height + 1)
                sleep(self.interval / 2 - (time() - start_time))

                # THEN COLLECT SIGNATURES AND SUBMIT BLOCK
                sigs = self.messenger.consume_sigs(height)
                if len(sigs) == 0:
                    print("could not get new block sigs")
                    continue
                self.generate_signed_block(block, sigs)

    def get_blockcount(self):
        try:
            return self.ocean.getblockcount()
        except Exception as e:
            print("{}\nReconnecting to client...".format(e))
            self.ocean = getelementsd(self.ocean_conf)
            return None

    def get_newblockhex(self):
        try:
            return self.ocean.getnewblockhex()
        except Exception as e:
            print("{}\nReconnecting to client...".format(e))
            self.ocean = getelementsd(self.ocean_conf)
            return None

    def get_blocksig(self, block):
        try:
            return self.ocean.signblock(block)
        except Exception as e:
            print("{}\nReconnecting to client...".format(e))
            self.ocean = getelementsd(self.ocean_conf)
            return None

    def generate_signed_block(self, block, sigs):
        try:
            sigs.append(self.get_blocksig(block))
            blockresult = self.ocean.combineblocksigs(block, sigs)
            signedblock = blockresult["hex"]
            self.ocean.submitblock(signedblock)
            print("node {} - submitted block {}".format(self.my_id, signedblock))
        except Exception as e:
            print("failed signing: {}".format(e))
