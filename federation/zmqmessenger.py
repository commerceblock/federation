#!/usr/bin/env python3
import zmq
import json
from .messenger import Messenger

TOPIC_NEW_BLOCK = '10'
TOPIC_NEW_SIG   = '20'

zmq_context = zmq.Context()
zmq_poller = zmq.Poller()

def mogrify(topic, msg):
    """ json encode the message and prepend the topic """
    return topic + ' ' + json.dumps(msg)

def demogrify(topicmsg):
    """ Inverse of mogrify() """
    json0 = topicmsg.find('{')
    topic = topicmsg[0:json0].strip()
    msg = json.loads(topicmsg[json0:])
    return topic, msg

class ZmqProducer:
    def __init__(self, port):
        self.socket = zmq_context.socket(zmq.PUB)
        self.socket.bind("tcp://127.0.0.1:%d" % port)
        zmq_poller.register(self.socket, zmq.POLLOUT)

    def send_message(self, msg, topic):
        #self.socket.send(mogrify(topic, msg).encode("ascii", "strict"))
        self.socket.send("{} {}".format(topic, msg).encode("ascii", "strict"), zmq.NOBLOCK)

class ZmqConsumer:
    def __init__(self, host, port, proxy=None):
        self.socket = zmq_context.socket(zmq.SUB)
        if proxy != None:
            self.socket.setsockopt(zmq.SOCKS_PROXY, proxy)
        self.socket.setsockopt(zmq.RECONNECT_IVL, 500)
        self.socket.setsockopt(zmq.RECONNECT_IVL_MAX, 10000)
        self.socket.connect("tcp://127.0.0.1:%d" % (port))
        self.socket.setsockopt(zmq.SUBSCRIBE, "{}".format(TOPIC_NEW_BLOCK).encode("ascii", "strict"))
        self.socket.setsockopt(zmq.SUBSCRIBE, "{}".format(TOPIC_NEW_SIG).encode("ascii", "strict"))
        zmq_poller.register(self.socket, zmq.POLLIN)

    def read_message(self):
        if self.socket not in dict(zmq_poller.poll()):
            return None, None
        #return demogrify(self.socket.recv().decode())
        return self.socket.recv().decode("ascii", "strict").split(" ", 1)

class ZmqMessenger(Messenger):
    def __init__(self, nodes, my_id):
        Messenger.__init__(self, nodes, my_id)
        self.consumers = []
        for i, node in enumerate(nodes):
            host, port = node.split(':', 1)
            if i == my_id:
                self.producer = ZmqProducer(int(port))
            else:
                self.consumers.append(ZmqConsumer(host, int(port)))

    def produce(self, topic, message):
        self.producer.send_message(message, topic)

    def produce_block(self, block, height):
        #message = {'height': height, 'block': block}
        self.produce(TOPIC_NEW_BLOCK, block)

    def produce_sig(self, sig, height):
        #message = {'height': height, 'sig': sig}
        self.produce(TOPIC_NEW_SIG, sig)

    def consume(self, topics):
        messages = []
        for consumer in self.consumers:
            while True:
                msg_topic, msg = consumer.read_message()
                if msg != None and msg_topic in topics:
                    messages.append(msg)
                else:
                    break
        return messages

    def consume_block(self, height):
        consumer = self.consume([TOPIC_NEW_BLOCK])
        if len(consumer) > 0:
            return consumer[-1]
        return None

    def consume_sigs(self, height):
        sigs = []
        consumer = self.consume([TOPIC_NEW_SIG])
        for message in consumer:
            sigs.append(message)
        return sigs
