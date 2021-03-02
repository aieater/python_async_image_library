#!/usr/bin/env python3
_dopen = open
from aimage.ui import *
from aimage.img import *
from aimage.head import *
import random
import time


class AggressiveImageGeneratorForOD:
    def __init__(self, datas, classes, data_aug_params, shuffle=True):
        self.classes = classes
        self.total = len(datas)
        self.q = 0
        self.iindex = 0
        self.oindex = 0
        self.datas = datas
        self.STREAM_BATCH = 16
        self.data_aug_params = data_aug_params
        self.output_buffer = []
        self.shuffle = shuffle
        self.stub_buffer = []

    def get_data_block(self, batch_size):
        if self.total == 0:
            raise "Zero length"
        while True:
            if self.q < 1024:
                if self.iindex < self.total:
                    ds = self.datas[self.iindex:self.iindex + self.STREAM_BATCH]
                    dlen = len(ds)
                    self.q += dlen
                    stream = list()
                    #input   = dict()
                    #input["data_aug_params"] = self.data_aug_params
                    for d in ds:
                        dd = dict()
                        dd["image_path"] = d["file_path"]
                        dd["image"] = load(d["file_path"])
                        dd["points_table"] = d["bounding_box_table"]
                        stream.append(dd)
                    #input["stream"] = stream
                    # //    {
                    # //      params:{
                    # //          data_aug_params:{}
                    # //      },
                    # //      stream: [{image_path:"",signals:[],points_table:[]},{},{},{},]
                    # //    }
                    # native_module.async_image_loader_with_data_aug_input(str(hex(id(self))),input)
                    self.stub_buffer += stream
                    #self.stub_buffer += [input]
                    # native_module.image_data_augmentation(input)
                    self.iindex += dlen
                else:
                    # random.shuffle(self.datas)
                    # self.iindex = 0
                    break
            else:
                break

        if self.iindex == self.oindex:
            return None
        if len(self.output_buffer) >= batch_size or self.iindex == self.oindex + len(self.output_buffer):
            buf = self.output_buffer[0:batch_size]
            self.output_buffer = self.output_buffer[batch_size:]
            self.oindex += len(buf)
            return buf
        while True:
            #ret = native_module.async_image_loader_with_data_aug_output(str(hex(id(self))))
            ret = self.stub_buffer
            if ret is not None and len(ret) > 0:
                for d in ret:
                    if "points_table" in d:
                        points_table = d["points_table"]
                        del d["points_table"]
                        d["bounding_box_table"] = points_table
                    else:
                        d["bounding_box_table"] = {}
                self.q -= len(ret)
                self.output_buffer += ret
                self.stub_buffer = []
                if len(self.output_buffer) >= batch_size or self.iindex == self.oindex + len(self.output_buffer):
                    buf = self.output_buffer[0:batch_size]
                    self.output_buffer = self.output_buffer[batch_size:]
                    self.oindex += len(buf)
                    return buf
            else:
                time.sleep(0.1)
                if self.iindex == self.oindex:
                    return None

    @staticmethod
    def make_full_aug_params():
        class Dict:
            def __init__(self):
                self.d = dict()

            def set(self, k, v):
                self.d[k] = str(v)

        d = Dict()
        FD = False
        if True:
            d.set("random_crop", 1 if FD else 0.25)  # @@
            d.set("crop_range", 0.2)  # @@
            d.set("random_median", 1 if FD else 0.1)  # @@
            d.set("random_color_reduction", 1 if FD else 0.1)  # @???
            d.set("random_equalization", 1 if FD else 0.1)

            d.set("random_bilateral", 1 if FD else 0.1)
            d.set("random_mosaic", 1 if FD else 0.1)
            d.set("mosaic_shift_range", 1)

            d.set("random_cos", 1 if FD else 0.1)
            d.set("random_hsv", 1 if FD else 0.5)
            d.set("hue_range", 15 if FD else 15)
            d.set("saturation_range", 0.05)
            d.set("lightness_range", 0.1)
            d.set("random_resize_and_arrange_images", 1 if FD else 0.1)
            d.set("random_horizontal_flip", 1 if FD else 0.15)
            d.set("random_vertical_flip", 1 if FD else 0.25)

            d.set("random_gaussian", 1 if FD else 0.1)
            d.set("random_sharp", 1 if FD else 0.1)
            d.set("random_pow", 1 if FD else 0.1)
            d.set("pow_min", 0.9)
            d.set("pow_max", 1.3)
            d.set("random_noise", 1 if FD else 0.1)
            d.set("random_erase", 1 if FD else 0.1)
            d.set("background_type", 3)
            d.set("affine_transform", 1)
            d.set("aggressive_transform", 0)
            d.set("random_z_rotate_range", 3)
            d.set("random_x_shift", 0.1)
            d.set("random_y_shift", 0.1)

        return d.d

    def sync_reset(self):
        if self.shuffle:
            random.shuffle(self.datas)
        self.iindex = 0
        self.oindex = 0

    @staticmethod
    def set_max_cache_size(size):
        pass
