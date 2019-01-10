#!/usr/bin/env python3
import os
import random
import sys
import time
import subprocess
import shutil
from .test_framework.authproxy import AuthServiceProxy, JSONRPCException

def startoceand(oceanpath, datadir, conf, args=""):
    subprocess.Popen((oceanpath+"  -datadir="+datadir+" "+args).split(), stdout=subprocess.PIPE)
    return getoceand(conf)

def getoceand(conf):
    if "rpcconnect" in conf:
        rpcconnect = conf["rpcconnect"]
    else:
        rpcconnect = "127.0.0.1"

    return AuthServiceProxy("http://"+conf["rpcuser"]+":"+conf["rpcpassword"]+"@"+rpcconnect+":"+conf["rpcport"])

def loadConfig(filename):
    conf = {}
    with open(filename) as f:
        for line in f:
            if len(line) == 0 or line[0] == "#" or len(line.split("=")) != 2:
                continue
            conf[line.split("=")[0]] = line.split("=")[1].strip()
    conf["filename"] = filename
    return conf
