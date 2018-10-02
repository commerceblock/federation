#!/usr/bin/env python3
from time import sleep, time
from .daemon import DaemonProcess
from .test_framework.authproxy import JSONRPCException
from .messenger_factory import MessengerFactory

class BlockSigning(DaemonProcess):
    def __init__(self, ocean, messenger_type, nodes, my_id, block_time):
        super().__init__()
        self.ocean = ocean
        self.interval = block_time
        self.total = len(nodes)
        self.my_id = my_id
        self.messenger = MessengerFactory.get_messenger(messenger_type, ocean, nodes, my_id)

    def run(self):
        while not self.stop_event.is_set():
            sleep(self.interval - time() % self.interval)
            start_time = int(time())
            step = int(time()) % (self.interval * self.total) / self.interval

            height = self.ocean.getblockcount()
            block = ""

            if self.my_id != int(step):
                # NOT OUR TURN - GET BLOCK AND SEND SIGNATURE ONLY
                print("node {} - consumer".format(self.my_id))
                sleep(self.interval / 4) # wait for new block
                new_block = self.messenger.consume_block(height)
                self.messenger.produce_sig(new_block, height + 1)
                sleep(self.interval / 2 - (time() - start_time))
            else:
                # OUR TURN - FIRST SEND NEW BLOCK HEX
                print("blockcount:{}".format(height))
                print("node {} - producer".format(self.my_id))
                block = self.ocean.getnewblockhex()
                self.messenger.produce_block(block, height + 1)
                sleep(self.interval / 2 - (time() - start_time))

                # THEN COLLECT SIGNATURES AND SUBMIT BLOCK
                sigs = self.messenger.consume_sigs(height)
                blockresult = self.ocean.combineblocksigs(block, sigs)
                signedblock = blockresult["hex"]
                try:
                    self.ocean.submitblock(signedblock)
                    print("node {} - submitted block {}".format(self.my_id, signedblock))
                except JSONRPCException as error:
                    print("failed signing: {}".format(error))
