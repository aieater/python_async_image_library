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
from io import BytesIO


DEBUG = False
def check_type(d,name):
    if DEBUG:
        print(name,type(d))

def to_bytes(d):
    if isinstance(d,bytes):
        return bytearray(d)
    if isinstance(d,bytearray):
        return d
    if isinstance(d,bytearray):
        return d
    if type(d).__module__ == np.__name__:
        return bytearray(d)
    return False


class StreamIO:
    def __init__(self):
        self.b = bytearray()
    def read(self,size=-1):
        b = self.b
        if size == -1:
            self.b = bytearray()
            return b
        bb = b[0:size]
        self.b = b[size:]
        return bb
    def getbuffer(self):
        return self.b
    def write(self,data):
        _data = to_bytes(data)
        slen = 0
        if _data:
            slen = len(_data)
            self.b.extend(_data)
            return slen
        else:
            ex = "expected type is bytes. Got object was " + str(type(data))
            print(ex)
            raise ex
        return slen

    def size(self):
        return len(self.b)


class DirectStream:
    def __init__(self):
        self.buffer = StreamIO()
    def write(self,data):
        return self.buffer.write(data)
    def read(self,size=-1):
        return self.buffer.read(size)
    def update(self):
        pass
    def info(self):
        return "DirectStream: TCP stream <bytes> => <bytes>"


class LengthSplitIn: # Stream(socket) to Blocks
    def __init__(self):
        self.buffer = StreamIO()
        self.blocks = []
    # stream to blocks
    def write(self,data):
        slen = len(data)
        check_type(data,"W:LengthSplitIn")
        self.buffer.write(data)
        buf = self.buffer.getbuffer()
        if len(buf) >= 4:
            slen = struct.unpack_from(">I", buf[0:4])[0]
            if slen > 1024*1024*10: #2MB
                print(slen)
                raise "too much data size"
            if len(buf) >= 4+slen:
                dummy = self.buffer.read(4)
                content = self.buffer.read(slen)
                self.blocks.append(content)
        return slen
    # blocks (extracted)
    def read(self,size=-1):
        if size == -1:
            blocks = self.blocks
            self.blocks = []
            return blocks
        blocks = self.blocks[0:size]
        self.blocks = self.blocks[size:]
        return blocks
    def update(self):
        pass
    def info(self):
        return "LengthSplitIn: Data block <bytes(<int,bytes,int,bytes,>)> => <[<bytes>,]>"


class LengthSplitOut: # Block(s) to Stream(socket)
    def __init__(self):
        self.buffer = StreamIO()
    # single data block to stream
    def write(self,blocks):
        check_type(blocks,"W:LengthSplitOut")
        tlen = 0
        for data in blocks:
            if isinstance(data,tuple):
                print(data)
            slen = len(data)
            blen = slen.to_bytes(4, 'big')
            self.buffer.write(blen)
            self.buffer.write(data)
            tlen += slen
        return tlen
    # stream (to socket)
    def read(self,size=-1):
        return self.buffer.read(size)
    def update(self):
        pass
    def info(self):
        return "LengthSplitOut: Data block <[<bytes>,]> => <bytes(<int,bytes,int,bytes,>)>"


class ImageDecoder: # Blocks to Blocks
    def __init__(self,*,queue_name="default"):
        self.input_blocks = []
        self.processing_map = {}
        self.output_blocks = []
        self.rcv_index = 0
        self.req_index = 0
        self.queue_name = queue_name

    def write(self,blocks):
        check_type(blocks,"W:ImageDecoder")
        slen = 0
        for data in blocks:
            slen += len(data)
            self.input_blocks.append(data)
        return slen
    def read(self,size=-1):
        if size == -1:
            blocks = self.output_blocks
            self.output_blocks = []
            return blocks
        blocks = self.output_blocks[0:size]
        self.output_blocks = self.output_blocks[size:]
        return blocks
    def update(self):
        if True:
            import aimage
            objs = []
            for b in self.input_blocks:
                objs.append({"input_buffer":b,"id":self.req_index})
                self.req_index+=1
            if len(objs) > 0: aimage.decode_input(objs,self.queue_name)
            self.input_blocks = []

            ret = aimage.decode_output(self.queue_name)
            if len(ret) > 0:
                for obj in ret:
                    self.processing_map[obj["index"]] = obj
            while True:
                obj = self.processing_map.pop(self.rcv_index,None)
                if obj:
                    self.output_blocks.append(obj["data"])
                    self.rcv_index+=1
                else:
                    break
        else:
            # for b in self.input_blocks: self.output_blocks.append(aimage.native_decoder(b))
            for b in self.input_blocks: self.output_blocks.append(aimage.opencv_decoder(b))
            self.input_blocks = []
    def info(self):
        return "ImageDecoder: Image data block <[<bytes>,]> => <[<ndarray>,]>"




class ImageEncoder: # Blocks to Blocks
    def __init__(self,*,queue_name="default",quality=90):
        self.input_blocks = []
        self.processing_map = {}
        self.output_blocks = []
        self.req_index = 0
        self.rcv_index = 0
        self.queue_name = queue_name
        self.quality = quality
    def write(self,blocks):
        slen = 0
        check_type(blocks,"W:ImageEncoder")
        for data in blocks:
            slen += len(data)
            self.input_blocks.append(data)
        return slen
    def read(self,size=-1):
        if size == -1:
            blocks = self.output_blocks
            self.output_blocks = []
            return blocks
        blocks = self.output_blocks[0:size]
        self.output_blocks = self.output_blocks[size:]
        return blocks
    def update(self):
        if True:
            import aimage
            objs = []
            for b in self.input_blocks:
                objs.append({"input_buffer":b,"id":self.req_index})
                self.req_index+=1
            if len(objs) > 0: aimage.encode_input(objs,self.quality,"jpg",self.queue_name)
            self.input_blocks = []

            ret = aimage.encode_output(self.queue_name)
            if len(ret) > 0:
                for obj in ret:
                    self.processing_map[obj["index"]] = obj
            while True:
                obj = self.processing_map.pop(self.rcv_index,None)
                if obj:
                    self.output_blocks.append(obj["data"])
                    self.rcv_index+=1
                else:
                    break
        else:
            # for b in self.input_blocks: self.output_blocks.append(aimage.native_encoder(b))
            for b in self.input_blocks: self.output_blocks.append(aimage.opencv_encoder(b))
            self.input_blocks = []
    def info(self):
        return "ImageEncoder: Image data block <[<ndarray>,]> => <[<bytes>,]>"


def protocols():
    print(DirectStream().info())
    print(LengthSplitIn().info())
    print(LengthSplitOut().info())
    print(ImageDecoder().info())
    print(ImageEncoder().info())


if __name__ == '__main__':
    print("=============================================")
    protocols()
    print("=============================================")
