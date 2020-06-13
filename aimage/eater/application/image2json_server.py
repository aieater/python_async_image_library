#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import signal
import time

import numpy as np

from ..bridge import server as ebs

parser = argparse.ArgumentParser(description='')
parser.add_argument('--inference', type=str, default="demo_object_detection", help='')
parser.add_argument('--ssl', action='store_true', help='')
parser.add_argument('--crt', type=str, default="", help='signed certificate file path')
parser.add_argument('--key', type=str, default="", help='private key file path')
parser.add_argument('--port', type=int, default=3000, help='')
parser.add_argument('--host', type=str, default="localhost", help='')
parser.add_argument('--quality', type=int, default=60, help='')
parser.add_argument('--dataset_dir', type=str, default="man2woman", help='')
args = parser.parse_args()


class ImageServer(ebs.EaterBridgeServer):
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.data_queue = []
        self.model = None
        print("Load Evaluator")
        import evaluator
        print("Instantiate Evaluator")
        self.model = evaluator.Evaluator()
        print("Evaluator Loaded")

    def update(self):
        new_datas = bridge.getDataBlocksAsArray()
        self.data_queue += new_datas
        if len(self.data_queue) > 0:
            batch_data, socket_mapper, self.data_queue = ebs.slice_as_batch_size(self.data_queue, 128)

            batch_data = np.uint8(batch_data)
            for i in range(len(batch_data)):
                img = batch_data[i]
                r_image = self.model.eval(img)
                batch_data[i] = r_image
            stored_datablocks = ebs.pack_array_datablock(socket_mapper, batch_data)
            bridge.setDataBlocksFromArray(stored_datablocks)

        return len(new_datas)


def server(args):
    return ImageServer(**args.__dict__)
