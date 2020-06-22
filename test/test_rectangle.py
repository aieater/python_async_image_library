#!/usr/bin/env python3

import aimage
import cv2
import os
import numpy as np
import gutil
import json


if __name__ == "__main__":
    img = np.zeros((512,512,3), dtype=np.uint8)
    aimage.draw_fill_rect(img, (0,100), (0, 200))
    aimage.draw_rect(img, (0,100), (0, 200))

    aimage.draw_title(img, "test")
    aimage.draw_footer(img, "test")
    
    print("Done")
