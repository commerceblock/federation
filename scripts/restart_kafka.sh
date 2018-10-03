# adit ~/.bash_profile and add kafka bin directory to $PATH

brew services stop kafka
kafka-topics --zookeeper localhost:2181 --delete --topic new-block
kafka-topics --zookeeper localhost:2181 --delete --topic new-sig0
kafka-topics --zookeeper localhost:2181 --delete --topic new-sig1
kafka-topics --zookeeper localhost:2181 --delete --topic new-sig2
brew services start kafka 
