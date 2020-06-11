#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import signal
import time

import numpy as np

from ..bridge import server as ebs

from easydict import EasyDict as edict


class ImageServer(ebs.EaterBridgeServer):
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.data_queue = []
        self.model = None
        import evaluator
        self.model = evaluator.Evaluator()

    def update(self):
        self.data_queue += self.getDataBlocksAsArray()
        if len(self.data_queue) > 0:
            batch_data, socket_mapper, self.data_queue = ebs.slice_as_batch_size(self.data_queue, 128)

            batch_data = np.uint8(batch_data)
            for i in range(len(batch_data)):
                img = batch_data[i]
                r_image = self.model.eval(img)
                batch_data[i] = r_image

            stored_datablocks = ebs.pack_array_datablock(socket_mapper, batch_data)
            self.setDataBlocksFromArray(stored_datablocks)


def server(args):
    return ImageServer(**args.__dict__)
