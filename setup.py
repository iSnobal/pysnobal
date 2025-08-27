#!/usr/bin/env python

import glob
import sys

import numpy as np
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as build_ext
from Cython.Build import cythonize

if sys.platform == "darwin":
    extra_compile_args = ["-Xpreprocessor", "-fopenmp", "-O3"]
    extra_link_args = ["-lomp"]
else:
    extra_compile_args = ["-fopenmp", "-O3"]
    extra_link_args = ["-fopenmp"]

sources = glob.glob(
    "pysnobal/c_snobal/libsnobal/*.c"
) + [
    "pysnobal/c_snobal/snobal.pyx"
]

extensions = [
    Extension(
        "pysnobal.c_snobal.snobal",
        sources=sources,
        include_dirs=[
            np.get_include(),
            "pysnobal/c_snobal",
            "pysnobal/c_snobal/h",
        ],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
]

setup(
    cmdclass={"build_ext": build_ext},
    ext_modules=cythonize(extensions, language_level="3"),
)