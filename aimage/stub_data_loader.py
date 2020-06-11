#!/usr/bin/env python3
_dopen = open
import glob
import json
import os
import pathlib
import random
import sys
import time

import cv2
import numpy as np
import tqdm
from aimage.head import *
from aimage.img import *
from aimage.ui import *
from easydict import EasyDict as edict


# Stub
class AggressiveImageGenerator:
    def __init__(self, **kwargs):
        """
        kwargs:
         - verbose: True / False # display detail
         - shuffle: True / False # shuffle data
         - entry: <input data path>
         - label_path: <output label path> for resume
         - loss: "tree" / "list" 
         - target_size: (w,h,c) # shape
         - data_align: True / False # adjust data length for each classes
         - rescale: 1/255.0
         - data_aug_params: dict{}
         - progress_bar: True / False
         - batch_size: 128
        """

        entry = kwargs["entry"]
        if entry == "/":
            print("\033[0;31m", "Error: Can't use root:", entry, "\033[0m")
            raise Exception("Can't specify root path")
        if entry[-1] == '/':
            print("\033[0;31m", entry, "\033[0m")
            entry = entry[0:-1]
        if entry == ".":
            print("\033[0;31m", "Error: Current directory:", entry, "\033[0m")
            raise Exception("Invalid path")
        if os.path.exists(entry) is False:
            print("\033[0;31m", "Error: Does not exist path:", entry, "\033[0m")
            raise Exception("Does not exist path")

        self.loss = "list"
        self.verbose = False
        self.progress_bar = True
        self.pbar = None
        self.shuffle = False
        self.batch_size = 128
        self.label_path = "output.label"
        self.target_size = (256, 256, 3)
        self.rescale = 1 / 255.0
        self.data_aug_params = {"resize_width": 256, "resize_height": 256}

        self.set(**kwargs)

        if self.verbose:
            print(kwargs)

        self.q = 0
        self.iindex = 0
        if self.verbose:
            print("=============================================")
        self.oindex = 0
        self.STREAM_BATCH = 16

        self.label_name = os.path.basename(self.entry)
        self.build_classes()

        if self.verbose:
            print(self.classes)

        data_aug_params = kwargs["data_aug_params"]

        def setd(k, v):
            if k not in data_aug_params:
                data_aug_params[k] = v

        setd("resize_interpolation", "fastest")
        for k in data_aug_params:
            data_aug_params[k] = str(data_aug_params[k])
        self.data_aug_params = data_aug_params

        self.stub_buffer = []
        self.output_buffer = []
        self.datas = None
        self.is_tree = self.loss == "tree"
        self.sync_reset()

    def shape(self):
        return self.target_size

    def length(self):
        return self.total

    def set_description(self, s):
        if self.pbar:
            self.pbar.set_description(s)
        pass

    def __iter__(self):
        self.ite = 0
        if self.pbar:
            self.pbar.refresh()
            self.pbar.close()
            self.pbar = None
        if self.progress_bar:
            self.pbar = tqdm.tqdm(total=self.length(), leave=True, file=sys.stdout)
        return self

    def __next__(self):
        if self.total > self.ite:
            ret = self.get_batch(self.batch_size)
            dlen = len(ret.images)
            if self.pbar:
                self.pbar.update(dlen)
            self.ite += dlen
            ret.ite = self.ite
            return ret
        else:
            if self.pbar:
                self.pbar.refresh()
                self.pbar.close()
                self.pbar = None
            self.sync_reset()
            raise StopIteration()

    def sync_reset(self):
        entry = self.entry
        if self.datas is None:
            self.datas = []
            self.prebatch = None
            class_index_table = {}
            table = {}
            for clazz in self.classes:
                c = self.classes[clazz]
                class_index_table[c["index"]] = {"name": clazz, "results": [], "total": 0}
            for filename in pathlib.Path(entry).glob('**/*.jpg'):
                filename = str(filename)
                self.datas.append(filename)
                signals = self.make_signal(self.entry, filename, self.classes)
                if self.is_tree:
                    signals *= self.signal_mask
                idx_key = np.argmax(signals)
                if idx_key not in table:
                    table[idx_key] = []
                table[idx_key].append(filename)
                # if idx_key not in class_index_table:
                #    class_index_table[idx_key] = {"name":self.get_name(idx_key),"results":[],"total":0}
                class_index_table[idx_key]["total"] += 1
            vmax = 0
            for k in table:
                v = table[k]
                vlen = len(v)
                if vlen > vmax:
                    vmax = vlen
                if self.verbose:
                    print(self.get_name(k), ":", vlen)
            if self.verbose:
                print("Max => ", vmax)
            for k in table:
                v = table[k]
                i = 0
                vlen = len(v)
                ns = []
                for x in range(vmax):
                    ns.append(v[x % vlen])
                table[k] = ns
            new_datas = []
            for k in table:
                v = table[k]
                vlen = len(v)
                new_datas += v
            if self.data_align:
                if self.verbose:
                    print("Total", len(self.datas), "=>", vmax, "x", len(table), "=>", len(new_datas))
                self.datas = new_datas
                for i in class_index_table:
                    class_index_table[i]["total"] = vmax
            self.total = len(self.datas)
            self.class_index_table = class_index_table
        if self.shuffle:
            random.shuffle(self.datas)
        self.iindex = 0
        self.oindex = 0

    def build_classes(self):
        j = {}
        try:
            j = json.loads(_dopen(self.label_path).read())
        except:
            pass
        classes = self.make_class(entry=self.entry, loss=self.loss, class_dict=j)
        self.label_json = json.dumps(classes)

        if os.path.exists(os.path.dirname(self.label_path)) is False:
            os.makedirs(os.path.dirname(self.label_path), exist_ok=True)

        with _dopen(self.label_path, "w") as fp:
            fp.write(self.label_json)

        self.classes = classes
        if self.loss == "tree":
            signal_mask = np.zeros((len(classes), ))
            tcnt = 0
            for clazz in classes:
                i = classes[clazz]["index"]
                if clazz[0] == "@":
                    signal_mask[i] = 1
                    tcnt += 1
            if tcnt <= 2:
                raise "Two or more target directories are required. Use @ to define it."
            self.signal_mask = signal_mask
        else:
            self.signal_mask = np.ones((len(classes), ))
        return classes

    def get_classes(self):
        return self.clasess

    def get_batch(self, batch_size=None):
        if batch_size is None:
            batch_size = self.batch_size
        block = self.get_data_block(batch_size)
        b = edict()
        b.images = []
        b.signals = []
        b.points = None
        b.file_paths = []
        if block:
            for d in block:
                b.images.append(d["image"])
                b.signals.append(d["signals"])
                b.file_paths.append(d["file_path"])
                #d["points"])
            b.images = np.array(b.images, dtype=np.float32)
            b.signals = np.array(b.signals, dtype=np.float32)
            if self.rescale != 1.0:
                b.images *= self.rescale

        return b

    def get_data_block(self, batch_size):
        if self.total == 0:
            print("Zero length")
            raise "Zero length"
        while True:
            if self.q < 1024:
                if self.iindex < self.total:
                    ds = self.datas[self.iindex:self.iindex + self.STREAM_BATCH]
                    dlen = len(ds)
                    self.q += dlen
                    stream = list()
                    # input   = dict()
                    # input["data_aug_params"] = self.data_aug_params
                    for image_path in ds:
                        signals = self.make_signal(self.entry, image_path, self.classes)
                        d = dict()
                        d["image_path"] = image_path
                        d["file_path"] = image_path
                        d["image"] = cv2.resize(load_image(image_path), (self.target_size[0], self.target_size[1]), interpolation=cv2.INTER_AREA)

                        # data_aug_params
                        # {'entry': 'data/fruit/train', 'label_path': 'weights/fruit.mobilenet.categorical_crossentropy.label', 'loss': 'categorical_crossentropy',
                        #     'target_size': (224, 224, 3), 'data_align': True, 'rescale': 0.00392156862745098, 'shuffle': True, 'data_aug_params': {'resize_width': 224, 'resize_height': 224}}

                        d["signals"] = np.array(signals, dtype=np.float32)
                        d["points_table"] = None
                        stream.append(d)
                    # input["stream"] = stream
                    # //    {
                    # //      params:{
                    # //          data_aug_params:{}
                    # //      },
                    # //      stream: [{image_path:"",signals:[],points_table:[]},{},{},{},]
                    # //    }
                    self.stub_buffer += stream
                    # native_module.async_image_loader_with_data_aug_input(str(hex(id(self))),input)
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
                self.q -= len(ret)
                self.output_buffer += ret
                if len(self.output_buffer) >= batch_size or self.iindex == self.oindex + len(self.output_buffer):
                    buf = self.output_buffer[0:batch_size]
                    self.output_buffer = self.output_buffer[batch_size:]
                    self.oindex += len(buf)
                    return buf
            else:
                time.sleep(0.1)
                if self.iindex == self.oindex:
                    return None

    def find_index(self, class_dict):
        index = 0
        d = sorted(class_dict.items(), key=lambda x: x[1]["index"])
        for obj in d:
            if index == int(obj[1]["index"]):
                index += 1
                continue
        return index

    def make_signal(self, entry, fpath, classes):
        sp = str(fpath)[len(entry):].split("/")
        signal = np.zeros((len(classes), ), dtype=np.float32)
        for s in sp:
            if s in classes:
                signal[classes[s]["index"]] = 1
        return signal

    def register_class(self, class_name, class_dict, mark):
        if class_name not in class_dict:
            index = self.find_index(class_dict)
            class_dict[class_name] = {"index": index}

    def make_class(self, entry, *, loss="tree", class_dict={}):
        if self.verbose:
            print("Entrypoint => ", entry)
        class_table_by_index = {}
        class_table_by_name = {}
        elen = len(entry)
        if self.verbose:
            print(loss)
        if loss == "list":
            class_names = [os.path.basename(f) for f in glob.glob(os.path.join(entry, "*")) if os.path.isdir(f)]
            # print(class_names)
            for class_name in class_names:
                self.register_class(class_name, class_dict, "S")
        elif loss == "tree":
            for filename in pathlib.Path(entry).glob('**/'):
                filename = str(filename)
                # {}Attributs/{@}Target/{!}Ignore/{?}Unsupervised
                if "/!" in filename:
                    print("Ignore", filename)
                    continue
                if filename == entry:
                    continue
                class_name = os.path.basename(filename)
                if class_name not in class_dict:
                    if class_name[0] == '@':
                        self.register_class(class_name, class_dict, mark="S")
                    elif class_name[0] == '?':
                        self.register_class(class_name, class_dict, mark=" ")
                    else:
                        self.register_class(class_name, class_dict, mark="-")
        else:
            raise "Inbalid loss"
        return class_dict

    def get_name(self, index):
        for k in self.classes:
            if index == self.classes[k]["index"]:
                return k
        return None

    def find_by_name(self, p, label_name):
        if label_name in self.classes:
            return p[self.classes[label_name]["index"]]
        return None

    def find_top(self, p):
        index = np.argmax(p)
        for k in self.classes:
            c = self.classes[k]
            if c["index"] == index:
                return index, p[index], k
        return None, None, None

    def set(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

    @staticmethod
    def make_full_aug_params():
        class Dict:
            def __init__(self):
                self.d = dict()

            def set(self, k, v):
                self.d[k] = str(v)

        d = Dict()
        d.set("random_gaussian", 0.1)
        d.set("random_sharp", 0.1)
        d.set("random_median", 0.1)
        d.set("random_bilateral", 0.1)
        d.set("random_mosaic", 0.1)
        d.set("mosaic_shift_range", 1)
        d.set("random_equalization", 0.1)
        d.set("random_color_reduction", 0.1)
        d.set("random_cos", 0.1)
        d.set("random_hsv", 0.5)
        d.set("hue_range", 15)
        d.set("saturation_range", 0.05)
        d.set("lightness_range", 0.1)
        d.set("random_pow", 0.1)
        d.set("pow_min", 0.9)
        d.set("pow_max", 1.3)
        d.set("random_horizontal_flip", 0.15)
        d.set("random_vertical_flip", 0.25)
        d.set("random_shuffle_splitted_images", 0.1)
        d.set("random_resize_and_arrange_images", 0.1)
        d.set("random_crop", 0.25)
        d.set("crop_range", 0.2)
        d.set("random_noise", 0.1)
        d.set("random_erase", 0.2)
        d.set("background_type", 5)
        d.set("affine_transform", 0.5)
        d.set("aggressive_transform", 0.5)
        d.set("random_x_shift", 0.1)
        d.set("random_y_shift", 0.1)
        d.set("random_x_scaling_range", 0.1)
        d.set("random_y_scaling_range", 0.1)
        d.set("random_x_rotate_range", 10)
        d.set("random_y_rotate_range", 10)
        d.set("random_z_rotate_range", 10)
        d.set("random_distortion", 0.5)
        d.set("random_mixup", 0.1)
        d.set("mixup_alpha", 0.1)
        return d.d

    @staticmethod
    def set_max_cache_size(size):
        pass
