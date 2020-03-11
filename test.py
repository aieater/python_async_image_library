#!/usr/bin/env python3

import cv2
import aimage
import os
import numpy as np
import gutil
import json

# DATASET_NAME = "CIFAR10"
# DATASET_NAME = "MNIST"
# DATASET_NAME = "FashionMNIST"
# DATASET_NAME = "anime-faces"
# DATASET_NAME = "face_mmd_frontal"
DATASET_NAME = "nk"
# DATASET_NAME = "cro"
# DATASET_NAME = "sc"

use_cache = True
DATA_DIR = os.path.join(os.path.expanduser("~/datas"), DATASET_NAME, "train")
#DATA_DIR = os.path.join(os.path.expanduser("~/datas"), DATASET_NAME)
STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATASET_NAME)
os.makedirs(STORE_DIR, exist_ok=True)
INPUT_SHAPE = (64, 64, 3)
LATENT_DIM = 2


def make_path(s): return os.path.join(os.path.dirname(os.path.abspath(__file__)), DATASET_NAME, s)


embedding_path = make_path("embedding.npy")
x_vectors_path = make_path("x_vectors.npy")
y_vectors_path = make_path("y_vectors.npy")
file_paths_path = make_path("file_paths.json")


if use_cache and os.path.exists(embedding_path) and os.path.exists(x_vectors_path) and os.path.exists(y_vectors_path) and os.path.exists(file_paths_path):
    embedding = np.load(embedding_path)
    print(embedding_path)
    x_vectors = np.load(x_vectors_path)
    print(x_vectors_path)
    y_vectors = np.load(y_vectors_path)
    print(y_vectors_path)
    with open(file_paths_path) as json_file:
        f_paths = json.load(json_file)["data"]
    print(file_paths_path)
else:
    x_vectors, y_vectors, f_paths = gutil.generate(INPUT_SHAPE, DATA_DIR)
    x = x_vectors.reshape(x_vectors.shape[0], -1)

    import warnings
    from numba.errors import NumbaPerformanceWarning
    warnings.filterwarnings("ignore", category=NumbaPerformanceWarning)
    import umap
    import sklearn

    print("--------------------------------------------------")
    print("- Learning..... UMAP")
    print("X :", x_vectors.shape)
    print("Y :", y_vectors.shape)
    print("O : ", (x_vectors.shape[0], LATENT_DIM))
    embedding = umap.UMAP(n_components=LATENT_DIM, n_neighbors=5, min_dist=0.3, metric='correlation').fit_transform(x)
    #embedding = sklearn.manifold.TSNE(n_components=2, random_state=0).fit_transform(x)
    print("--------------------------------------------------")
    print("- Save numpy arrays.")

    np.save(embedding_path, embedding)
    print(embedding_path)
    np.save(x_vectors_path, x_vectors)
    print(x_vectors_path)
    np.save(y_vectors_path, y_vectors)
    print(y_vectors_path)

    with open(file_paths_path, 'w') as outfile:
        json.dump({"data": f_paths}, outfile)
    print(file_paths_path)

print("Plotting...")
gutil.plot(embedding, x_vectors, y_vectors, f_paths)
