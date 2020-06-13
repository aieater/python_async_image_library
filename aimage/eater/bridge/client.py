#!/usr/bin/env python3
import math
import queue
import threading
import traceback
import uuid

from twisted.internet import protocol, reactor, ssl

from ..bridge import protocol as bp



def success(*args, **kwargs):
    print('\033[0;32m', *args, '\033[0m', **kwargs)


def warn(*args, **kwargs):
    print('\033[0;31m', *args, '\033[0m', **kwargs)


def info(*args, **kwargs):
    print('\033[0;36m', *args, '\033[0m', **kwargs)


def estimate_retry_delay_time(r, max_delay=20):
    s = math.exp(r)
    return s if s < 20 else 20


class StackedClientSocketProtocol(protocol.Protocol):
    def __init__(self, rq, wq):
        self.rq = rq
        self.wq = wq
        self.input_middlewares = []
        self.output_middlewares = []
        self.is_available = False
        self.is_invalid_socket = False
        self.queue_name = "default"

    def add_input_protocol(self, p):
        p.queue_name = self.queue_name
        self.input_middlewares.append(p)

    def add_output_protocol(self, p):
        p.queue_name = self.queue_name
        self.output_middlewares.append(p)

    def connectionMade(self):
        import aimage
        aimage.create_queue(self.queue_name)
        self.is_available = True

    def connectionLost(self, reason):
        import aimage
        aimage.delete_queue(self.queue_name)
        self.is_available = False

    def dataReceived(self, data):
        info("TCP:READ:", data)
        if self.is_available:
            self.input_middlewares[0].write(data)

    def update(self):
        if self.is_invalid_socket: return
        try:
            # From opponent
            for i in range(len(self.input_middlewares) - 1):
                b = self.input_middlewares[i].read()
                if len(b):
                    self.input_middlewares[i + 1].write(b)
            for m in self.input_middlewares:
                m.update()
            # To opponent
            for i in range(len(self.output_middlewares) - 1):
                b = self.output_middlewares[i].read()
                if len(b):
                    self.output_middlewares[i + 1].write(b)
            for m in self.output_middlewares:
                m.update()
            buf = self.output_middlewares[-1].read(-1)
            if self.is_available and len(buf) > 0:
                self.transport.write(buf)
                info("TCP:WRITE:", buf)
        except Exception as e:
            print(e)
            self.is_invalid_socket = True
            try:
                self.transport.close()
                self.wq.clear()
                self.rq.clear()
            except Exception as e:
                print(e)
        while self.rq.empty() is False:
            o = self.rq.get_nowait()
            self.output_middlewares[0].write(o)

        b = self.input_middlewares[-1].read(-1)
        if len(b) > 0:
            self.wq.put_nowait(b)


class StreamClientFactory(protocol.ClientFactory):
    def __init__(self, rq, wq, **kwargs):
        self.rq = rq
        self.wq = wq
        self.retry = 0
        self.retying = False
        self.connected = False
        self.protocol_instance = None
        self.addr = None
        self.kwargs = kwargs
        self.update()

    def startedConnecting(self, connector):
        info(f'Started to connect. {connector.host}:{connector.port} Timeout:{connector.timeout}')

    # Override
    def on_disconnected(self):
        pass

    # Override
    def on_connected(self):
        self.protocol_instance.add_input_protocol(bp.DirectStream())
        self.protocol_instance.add_output_protocol(bp.DirectStream())

    def buildProtocol(self, addr):
        self.addr = addr
        self.retry = 0
        self.retying = False
        self.connected = True
        success('Connected', addr)
        s = StackedClientSocketProtocol(self.rq, self.wq)
        # s.input_middlewares.append(bp.DirectStream())
        # s.output_middlewares.append(bp.DirectStream())
        s.queue_name = str(uuid.uuid4())
        self.protocol_instance = s
        # s.input_middlewares.append(bp.LengthSplitIn())
        # s.output_middlewares.append(bp.LengthSplitOut())
        self.on_connected()
        return s

    def update(self):
        if self.protocol_instance:
            self.protocol_instance.update()
            if self.protocol_instance.is_invalid_socket:
                self.protocol_instance = None
        reactor.callLater(0.001, self.update)

    def deffered_connect(self, args):
        if self.retying is False and self.connected is False:
            self.retying = True
            self.retry += 1
            args[0].connect()

    def clientConnectionLost(self, connector, reason):
        delay = estimate_retry_delay_time(self.retry)
        warn(f'Lost connection. RetryDelay:[{self.retry}]:{round(delay,2)}s\n  Reason:', reason)
        self.on_disconnected()
        self.connected = False
        self.retying = False
        reactor.callLater(delay, self.deffered_connect, (connector, ))

    def clientConnectionFailed(self, connector, reason):
        delay = estimate_retry_delay_time(self.retry)
        warn(f'Connection failed. RetryDelay:[{self.retry}]:{round(delay,2)}s\n  Reason:', reason)
        self.on_disconnected()
        self.connected = False
        self.retying = False
        reactor.callLater(delay, self.deffered_connect, (connector, ))


class EaterBridgeClient:
    def __init__(self, **kargs):
        self.kargs = kargs
        self.host = kargs["host"]
        self.port = kargs["port"]
        self.rq = queue.Queue()
        self.wq = queue.Queue()
        self.protocol_stack = kargs["protocol_stack"](self.rq, self.wq, **self.kargs)

    def start(self):
        self.deffered = reactor.connectTCP(self.host, self.port, self.protocol_stack)
        # self.deffered = reactor.connectSSL(self.host, self.port, StreamClientFactory(self.rq,self.wq),ssl.ClientContextFactory())
        self.thread = threading.Thread(target=reactor.run, args=(False, ))
        self.thread.setDaemon(True)
        self.thread.start()

    def destroy(self):
        reactor.stop()

    def write(self, blocks):
        if self.rq.empty():
            self.rq.put(blocks)
            return True
        return False

    def read(self, size=-1):
        if self.wq.empty() is False:
            return self.wq.get()
        return None
