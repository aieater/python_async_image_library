#!/usr/bin/env python3

from aimage.head import *
from aimage.img import *
from aimage.ui import *
from aimage.stub_data_loader_od import *
from aimage.stub_data_loader import *


try:
    from aimage_native import *
    print('\033[0;36m' + "========================================================" + '\033[0m')
    print('\033[0;36m' + "Aggressive 3D image augmentation is available." + '\033[0m')
    print('\033[0;36m' + "Fastest async image loader is available." + '\033[0m')
    print('\033[0;36m' + "aimage loading speed is faster than Pillow/OpenCV/TensorFlow." + '\033[0m')
    print('\033[0;36m' + "Event driven non blocking loader is available." + '\033[0m')
    print('\033[0;36m' + "========================================================" + '\033[0m')
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
