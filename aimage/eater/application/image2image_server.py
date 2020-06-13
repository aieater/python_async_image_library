#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import signal
import time

import numpy as np
import uuid
from ..bridge import server as ebs
from ..bridge import protocol as bp

from easydict import EasyDict as edict


class ProtocolStack(ebs.StreamFactory):
    def build_protocol_stack(self, s):
        s.add_input_protocol(bp.LengthSplitIn())
        s.add_input_protocol(bp.ImageDecoder())
        s.add_output_protocol(bp.ImageEncoder(quality=60))
        s.add_output_protocol(bp.LengthSplitOut())


class ImageServer(ebs.EaterBridgeServer):
    def __init__(self, **kargs):
        kargs["protocol_stack"] = ProtocolStack
        super().__init__(**kargs)
        self.data_queue = []
        self.model = None

    def update(self):
        if self.model is None:
            import evaluator
            self.model = evaluator.Evaluator()
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
