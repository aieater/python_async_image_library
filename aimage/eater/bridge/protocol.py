#!/usr/bin/env python3
import numpy as np
import struct

DEBUG = False


def check_type(d, name):
    if DEBUG:
        print(name, type(d))


def to_bytes(d):
    if isinstance(d, bytes):
        return bytearray(d)
    if isinstance(d, bytearray):
        return d
    if isinstance(d, str):
        return d.encode('utf-8')
    if isinstance(d, list):
        return bytearray(d)
    if type(d).__module__ == np.__name__:
        return bytearray(d)
    return False


class StreamIO:
    def __init__(self):
        self.b = bytearray()

    def read(self, size=-1):
        _b = self.b
        if size == -1:
            # Return all
            self.b = bytearray()
            return _b
        # Return sliced buffer
        bb = _b[0:size]
        self.b = _b[size:]
        return bb

    def getbuffer(self):
        return self.b

    def write(self, data):
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

    def length(self):
        return len(self.b)


class DirectStream:
    def __init__(self):
        self.queue_name = None
        self.buffer = StreamIO()

    def write(self, data):
        return self.buffer.write(data)

    def read(self, size=-1):
        return self.buffer.read(size)

    def update(self):
        pass

    def info(self):
        return "DirectStream: TCP stream <bytes> => <bytes>"


class LengthSplitIn:  # Stream(socket) to Blocks
    def __init__(self, max_buffer_size=1024 * 1024 * 10):
        self.queue_name = None
        self.buffer = StreamIO()
        self.blocks = []
        self.max_buffer_size = max_buffer_size

    # stream to blocks
    def write(self, data):
        slen = len(data)
        blen = self.buffer.length()
        check_type(data, "W:LengthSplitIn")
        if slen + blen > self.max_buffer_size:
            print("LengthSplitIn:write", "Data size:", slen, "Buffer size:", blen)
            raise Exception("too much data size")
        self.buffer.write(data)
        buf = self.buffer.getbuffer()
        # More than header size
        if len(buf) >= 4:
            body_length = struct.unpack_from(">I", buf[0:4])[0]
            # Has contents
            if len(buf) >= 4 + body_length:
                head = self.buffer.read(4)
                body = self.buffer.read(body_length)
                print("LengthSplitIn:write:", body)
                self.blocks.append(body)
        return slen

    # blocks (extracted)
    def read(self, size=-1):
        if size == -1:
            _blocks = self.blocks
            self.blocks = []
            return _blocks
        _blocks = self.blocks[0:size]
        self.blocks = self.blocks[size:]
        return _blocks

    def update(self):
        pass

    def info(self):
        return "LengthSplitIn: Data block <bytes(<int,bytes,int,bytes,>)> => <[<bytes>,]>"


class LengthSplitOut:  # Block(s) to Stream(socket)
    def __init__(self, max_buffer_size=1024 * 1024 * 10):
        self.queue_name = None
        self.buffer = StreamIO()
        self.max_buffer_size = max_buffer_size

    # single data block to stream
    def write(self, blocks):
        check_type(blocks, "W:LengthSplitOut")

        tlen = 0
        blen = self.buffer.length()
        for data in blocks:
            tlen += len(data)
        if tlen + blen > self.max_buffer_size:
            print("LengthSplitOut:write", "Data size:", tlen, "Buffer size:", blen)
            raise Exception("too much data size")

        for data in blocks:
            slen = len(data)
            blen = slen.to_bytes(4, 'big')
            self.buffer.write(blen)
            self.buffer.write(data)

        return tlen

    # stream (to socket)
    def read(self, size=-1):
        return self.buffer.read(size)

    def update(self):
        pass

    def info(self):
        return "LengthSplitOut: Data block <[<bytes>,]> => <bytes(<int,bytes,int,bytes,>)>"


class ImageDecoder:  # Blocks to Blocks
    def __init__(self, *, queue_name="default"):
        self.input_blocks = []
        self.processing_map = {}
        self.output_blocks = []
        self.rcv_index = 0
        self.req_index = 0
        self.queue_name = queue_name

    def write(self, blocks):
        check_type(blocks, "W:ImageDecoder")
        slen = 0
        for data in blocks:
            slen += len(data)
            self.input_blocks.append(data)
        return slen

    def read(self, size=-1):
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
                objs.append({"input_buffer": b, "id": self.req_index})
                self.req_index += 1
            if len(objs) > 0: aimage.decode_input(objs, self.queue_name)
            self.input_blocks = []

            ret = aimage.decode_output(self.queue_name)
            if len(ret) > 0:
                for obj in ret:
                    self.processing_map[obj["index"]] = obj
            while True:
                obj = self.processing_map.pop(self.rcv_index, None)
                if obj:
                    self.output_blocks.append(obj["data"])
                    self.rcv_index += 1
                else:
                    break
        else:
            # for b in self.input_blocks: self.output_blocks.append(aimage.native_decoder(b))
            for b in self.input_blocks:
                self.output_blocks.append(aimage.opencv_decoder(b))
            self.input_blocks = []

    def info(self):
        return "ImageDecoder: Image data block <[<bytes>,]> => <[<ndarray>,]>"


class ImageEncoder:  # Blocks to Blocks
    def __init__(self, *, queue_name="default", quality=90):
        self.input_blocks = []
        self.processing_map = {}
        self.output_blocks = []
        self.req_index = 0
        self.rcv_index = 0
        self.queue_name = queue_name
        self.quality = quality

    def write(self, blocks):
        slen = 0
        check_type(blocks, "W:ImageEncoder")
        for data in blocks:
            slen += len(data)
            self.input_blocks.append(data)
        return slen

    def read(self, size=-1):
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
                objs.append({"input_buffer": b, "id": self.req_index})
                self.req_index += 1
            if len(objs) > 0: aimage.encode_input(objs, self.quality, "jpg", self.queue_name)
            self.input_blocks = []

            ret = aimage.encode_output(self.queue_name)
            if len(ret) > 0:
                for obj in ret:
                    self.processing_map[obj["index"]] = obj
            while True:
                obj = self.processing_map.pop(self.rcv_index, None)
                if obj:
                    self.output_blocks.append(obj["data"])
                    self.rcv_index += 1
                else:
                    break
        else:
            # for b in self.input_blocks: self.output_blocks.append(aimage.native_encoder(b))
            for b in self.input_blocks:
                self.output_blocks.append(aimage.opencv_encoder(b))
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
