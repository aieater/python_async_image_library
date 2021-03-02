from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))

version = '1.3.10'

install_requires = [
    # 'termios',
    #'opencv-python',
    #'pygame',
    #'PyOpenGL',
    'mss',
    'configparser',
    'imgcat',
    'acapture',
    'twisted',
    'tqdm',
    'numpy',
    'psutil',
    'easydict',
    'service_identity',
]

readme = open("README.md").read()

setup(name='aimage',
    version=version,
    description="Native aimage library wrapper for internal use.",
    long_description="https://github.com/aieater/python_async_image_library\n\n"+readme,
    long_description_content_type='text/markdown',
    classifiers=(
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ),
    keywords='async video image computer vision deeplearning machinelarning augmentation',
    author='Pegara, Inc.',
    author_email='support@pegara.com',
    url='https://github.com/aieater/python_async_image_library',
    license='MIT',
    packages=['aimage','aimage.eater.bridge', 'aimage.eater.application'],
    zip_safe=False,
    install_requires=install_requires,
    entry_points={}
)
