#!/bin/sh
set -e

if [ "$HOST" = "universal2-apple-darwin" ]; then
    ./configure --disable-shared --enable-static --prefix=$PREFIX --with-pic
else
    ./configure --disable-shared --enable-static --host=$HOST --prefix=$PREFIX --with-pic
fi

make -j $CPU_COUNT
make install
