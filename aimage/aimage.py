#!/usr/bin/env python3

from aimage.head import *
from aimage.img import *
from aimage.ui import *
from aimage.stub_data_loader_od import *
from aimage.stub_data_loader import *

is_native = False
is_available_native_queue = False


def rebuild_worker(n):
    print("stub:rebuild_worker")


def create_queue(n):
    print("stub:create_queue")


def native_decoder(data):
    print("stub:native_decoder")


def native_encoder(data, *, quality=90, format="jpg"):
    print("stub:native_encoder")


def native_fast_decoder(data):
    print("stub:native_fast_decoder")


def native_fast_encoder(data, *, quality=90, format="jpg"):
    print("stub:native_fast_encoder")


def native_load_image(path):
    print("stub:native_load_image")


def native_save_image(path, data, *, quality=90, format="jpg"):
    print("stub:native_save_image")


def native_fast_load_image(path):
    print("stub:native_fast_load_image")


def native_fast_save_image(path, data, *, quality=90, format="jpg"):
    print("stub:native_fast_save_image")


try:
    from aimage_native import *
    print('\033[0;36m' + "========================================================" + '\033[0m')
    print('\033[0;36m' + "Aggressive 3D image augmentation is available." + '\033[0m')
    print('\033[0;36m' + "Fastest async image loader is available." + '\033[0m')
    print('\033[0;36m' + "aimage loading speed is faster than Pillow/OpenCV/TensorFlow." + '\033[0m')
    print('\033[0;36m' + "Event driven non blocking loader is available." + '\033[0m')
    print('\033[0;36m' + "========================================================" + '\033[0m')
    is_native = True
except:
    print('\033[0;31m' + "aimage_native library failed to load." + '\033[0m')
    print('\033[0;31m' + "===========================================================================" + '\033[0m')
    print('\033[0;31m' + "WARN: Native async image library loading failed." + '\033[0m')
    print('\033[0;31m' + " - Pillow/OpenCV/TensorFlow data loading speed is slower than aimage library." + '\033[0m')
    print('\033[0;31m' + " - aimage is superior to the data augmentation systems built into DeepLearning frameworks such as TensorFlow and PyTorch." + '\033[0m')
    print('\033[0;31m' + " If you want to get suport for paid license, please contact support@pegara.com." + '\033[0m')
    print('\033[0;31m' + "===========================================================================" + '\033[0m')
    print()
    print('\033[0;31m' + "Using unoptimized aimage library." + '\033[0m')
    print()
    pass

if __name__ == "__main__":

    pass
