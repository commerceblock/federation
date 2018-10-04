#!/usr/bin/env python3
import json
from .messenger import Messenger
from kafka import KafkaConsumer, KafkaProducer

KAFKA_SERVER    = 'kafka:9092'
TOPIC_NEW_BLOCK = 'new-block'
TOPIC_NEW_SIG   = 'new-sig'

class KafkaMessenger(Messenger):
    def __init__(self, nodes, my_id):
        Messenger.__init__(self, nodes, my_id)
        self.my_sig_topic = TOPIC_NEW_SIG + "{}".format(my_id)
        self.all_sig_topics = [TOPIC_NEW_SIG + "{}".format(i) for i in range(len(nodes))]

    def produce(self, topic, message):
        producer = KafkaProducer(bootstrap_servers=KAFKA_SERVER,
                                value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        producer.send(topic, message)
        producer.close()

    def consume(self, topics):
        consumer = KafkaConsumer(bootstrap_servers=KAFKA_SERVER,
                                 auto_offset_reset='earliest',
                                 consumer_timeout_ms=1000,
                                 value_deserializer=lambda m: json.loads(m.decode('utf-8')))
        consumer.subscribe(topics)
        return consumer

    def produce_block(self, block, height):
        message = {'height': height, 'block': block}
        self.produce(TOPIC_NEW_BLOCK, message)

    def produce_sig(self, sig, height):
        message = {'height': height, 'sig': sig}
        self.produce(self.my_sig_topic, message)

    def consume_block(self, height):
        consumer = self.consume([TOPIC_NEW_BLOCK])
        for message in consumer:
            message_height = int(message.value.get("height", 0))
            if message_height > height: # just in case to avoid old messages
                new_block = message.value.get("block", "")
                return new_block
        return None

    def consume_sigs(self, height):
        consumer = self.consume(self.all_sig_topics)
        sigs = []
        try:
            for message in consumer:
                if message.topic in self.all_sig_topics and int(message.value.get("height", 0)) > height:
                    sigs.append(message.value.get("sig", ""))
        except Exception as ex:
            print("serialization failed {}".format(ex))
        return sigs
