#!/bin/sh
set -e

# -e is needed to override explicit assignment to CC, CFLAGS etc. in the Makefile.
make -e -j $CPU_COUNT bzip2 bzip2recover
make install PREFIX=$PREFIX
