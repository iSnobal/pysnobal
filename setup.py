#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os
import sys

import numpy
from setuptools import setup, Extension
from Cython.Distutils import build_ext

# Allow user to specify a compiler; default to gcc if not provided
os.environ.setdefault("CC", "gcc")

# macOS: adjust linker flags for shared libs
if sys.platform == "darwin":
    from distutils import sysconfig
    vars = sysconfig.get_config_vars()
    if vars.get("LDSHARED"):
        vars["LDSHARED"] = vars["LDSHARED"].replace("-bundle", "-dynamiclib")

# Collect sources
c_sources = glob.glob("pysnobal/c_snobal/libsnobal/*.c")
pyx_source = "pysnobal/c_snobal/snobal.pyx"
sources = c_sources + [pyx_source]

extra_cc_args = ["-fopenmp", "-O3", "-L./pysnobal"]

extensions = [
    Extension(
        "pysnobal.c_snobal.snobal",
        sources=sources,
        include_dirs=[
            numpy.get_include(),
            "pysnobal/c_snobal",
            "pysnobal/c_snobal/h",
        ],
        extra_compile_args=extra_cc_args,
        extra_link_args=extra_cc_args,
    )
]

setup(
    cmdclass={"build_ext": build_ext},
    ext_modules=extensions,
)