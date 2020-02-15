import numpy as np
class Evaluator():
    def __init__(self):
        #self.model = yolov3.YOLO()
        pass
    def eval(self,img):
        return img
        r_image = self.model.detect_image(img)
        r_image = np.asarray(r_image)
        return r_image


