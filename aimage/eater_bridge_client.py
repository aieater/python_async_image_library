#!/usr/bin/env python3
from __future__ import print_function
import os
def to_bool(s): return s in [1,'True','TRUE','true','1','yes','Yes','Y','y','t','on']
import inspect
DEBUG = False
if "DEBUG" in os.environ:
    DEBUG = to_bool(os.environ["DEBUG"])
    if DEBUG:
        try: import __builtin__
        except ImportError: import builtins as __builtin__
        import inspect
        def lpad(s,c): return s[0:c].ljust(c)
        def rpad(s,c):
            if len(s) > c: return s[len(s)-c:]
            else: return s.rjust(c)
        def print(*args, **kwargs):
            s = inspect.stack()
            __builtin__.print("\033[44m%s@%s(%s):\033[0m " % (rpad(s[1][1], 20), lpad(str(s[1][3]), 10), rpad(str(s[1][2]), 4)), end="")
            return __builtin__.print(*args, **kwargs)
def _pre_(): print("\033[A                                                                \033[A",flush=True)


from twisted.internet import reactor, protocol, endpoints
from twisted.protocols import basic

from twisted.internet import ssl, reactor


import traceback
import uuid
import cv2
import threading
import queue
import time
import struct
import numpy as np
import signal
import math
from bridge_protocol import StreamIO


import bridge_protocol as bp



class StackedClientSocketProtocol(protocol.Protocol):
    def __init__(self, rq, wq):
        self.listener = None
        self.rq = rq
        self.wq = wq
        self.input_middlewares = []
        self.output_middlewares = []
        self.is_available = False
        self.is_invalid_socket = False
        self.queue_name = "default"

    def connectionMade(self):
        import aimage
        aimage.create_queue(self.queue_name)
        self.is_available = True
        if self.listener:
            self.listener.disconnected(self)
    def connectionLost(self, reason):
        import aimage
        aimage.delete_queue(self.queue_name)
        self.is_available = False
        if self.listener:
            self.listener.connected(self)
    def dataReceived(self, data):
        if self.is_available:
            self.input_middlewares[0].write(data)
    def update(self):
        if self.is_invalid_socket: return
        try:
            # From opponent
            for i in range(len(self.input_middlewares)-1):
                b = self.input_middlewares[i].read()
                if len(b):
                    self.input_middlewares[i+1].write(b)
            for m in self.input_middlewares:
                m.update()
            # To opponent
            for i in range(len(self.output_middlewares)-1):
                b = self.output_middlewares[i].read()
                if len(b):
                    self.output_middlewares[i+1].write(b)
            for m in self.output_middlewares:
                m.update()
            buf = self.output_middlewares[-1].read(-1)
            if self.is_available and len(buf) > 0:
                self.transport.write(buf)
        except:
            traceback.print_exc()
            self.is_invalid_socket = True
            try:
                self.transport.close()
                self.wq.clear()
                self.rq.clear()
            except:
                pass
        while self.rq.qsize()>0:
            self.output_middlewares[0].write(self.rq.get())
        b = self.input_middlewares[-1].read(-1)
        if len(b) > 0:
            self.wq.put(b)

class StreamClientFactory(protocol.ClientFactory):
    def __init__(self,rq,wq,**kwargs):
        self.rq = rq
        self.wq = wq
        self.retry = 0
        self.retying = False
        self.connected = False
        self.protocol_instance = None
        self.addr = None
        print(kwargs)
        self.kwargs = kwargs
        self.quality = kwargs["quality"]
        self.listener = kwargs["listener"]
        self.update()
    def startedConnecting(self, connector):
        print('Started to connect.',self.addr)
    def buildProtocol(self, addr):
        self.addr = addr
        self.retry = 0
        self.retying = False
        self.connected = True
        print('Connected',addr)
        s = StackedClientSocketProtocol(self.rq,self.wq)
        # s.input_middlewares.append(bp.DirectStream())
        # s.output_middlewares.append(bp.DirectStream())
        s.listener = self.listener
        s.queue_name = str(uuid.uuid4())
        s.input_middlewares.append(bp.LengthSplitIn())
        s.input_middlewares.append(bp.ImageDecoder(queue_name=s.queue_name))
        s.output_middlewares.append(bp.ImageEncoder(queue_name=s.queue_name,quality=self.quality))
        s.output_middlewares.append(bp.LengthSplitOut())

        # s.input_middlewares.append(bp.LengthSplitIn())
        # s.output_middlewares.append(bp.LengthSplitOut())
        self.protocol_instance = s
        return s
    def update(self):
        if self.protocol_instance:
            self.protocol_instance.update()
            if self.protocol_instance.is_invalid_socket:
                self.protocol_instance = None
        reactor.callLater(0.001, self.update)
    def deffered_connect(self,args):
        if self.retying == False and self.connected == False:
            self.retying = True
            self.retry += 1
            args[0].connect()
    def clientConnectionLost(self, connector, reason):
        print('Lost connection.  Reason:', reason)
        self.connected = False
        self.retying = False
        print(math.exp(self.retry))
        reactor.callLater(math.exp(self.retry), self.deffered_connect,(connector,))
    def clientConnectionFailed(self, connector, reason):
        print('Connection failed. Reason:', reason)
        self.connected = False
        self.retying = False
        reactor.callLater(math.exp(self.retry), self.deffered_connect,(connector,))

class EaterBridgeClient:
    def __init__(self,**kargs):
        self.kargs = kargs
        self.listener = kargs["listener"]
        self.host = kargs["host"]
        self.port = kargs["port"]
        self.rq = queue.Queue()
        self.wq = queue.Queue()
        self.start()
    def start(self):
        print("Start client")
        self.deffered = reactor.connectTCP(self.host, self.port, StreamClientFactory(self.rq,self.wq,**self.kargs))
        # self.deffered = reactor.connectSSL(self.host, self.port, StreamClientFactory(self.rq,self.wq),ssl.ClientContextFactory())
        print("Processing on background")
        self.thread = threading.Thread(target=reactor.run,args=(False,))
        self.thread.setDaemon(True)
        self.thread.start()
    def write(self,blocks):
        if self.rq.qsize()<1:
            self.rq.put(blocks)
            return True
        return False
    def read(self,size=-1):
        if self.wq.qsize() > 0:
            return self.wq.get()
        return []

def terminated(a,b):
    exit(9)
    pass
signal.signal(signal.SIGINT, terminated)
