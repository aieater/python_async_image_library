#!/usr/bin/env python3

import time
import aimage
import cv2
import os
import unittest



class Test(unittest.TestCase):
    def image_io_jpg(self):
        img = np.zeros((256, 256, 3), dtype=np.uint8)
        aimage.save_image(".tmp.jpg", img)
        aimage.load_image(".tmp.jpg", img)

    def image_io_png(self):
        img = np.zeros((256, 256, 3), dtype=np.uint8)
        aimage.save_image(".tmp.png", img)
        aimage.load_image(".tmp.png", img)




#unittest.main()


g = aimage.AggressiveImageGenerator(
    entry=os.path.join("/Users/akihito/projects/tmp/test"),
    label_path=os.path.join("/Users/akihito/projects/tmp", "output.json"),
    loss="categorical_crossentropy",
    target_size=(28, 28, 3),
    data_align=False,  # adjust data length for each classes
    rescale=1/255.0,
    shuffle=True,
    verbose=False,
    batch_size=4,
    progress_bar=True,
    data_aug_params={}
)

for x,y,z,i in g:
    print(x.shape)
    for img in x:
        aimage.show(img*255)
        aimage.wait(0)


