# CPython deps

A meta-package for building the binary packages that are required to compile
CPython on Android, iOS and macOS. This includes:

* BZip2
* XZ
* libFFI
* mpdecimal
* OpenSSL 1.1
* OpenSSL 3.0

The repository works by downloading, patching, and building binaries for each
SDK target and architecture that is requried. The compiled library is packed
into a tarball for distribution in "installed" form - that is, the contents of
the `include` and `lib` folders are included.

The binaries support:
* Android 21
  - ARM64
  - armv7
  - x86_64
  - x86
* iOS 13.0
  - ARM64 devices
  - ARM64 simulators
  - x86_64 simulators
* macOS 11.0
  - "universal2" ARM64+x86_64

## Quickstart

**Unless you're trying to directly link against one of these libraries, you
don't need to use this repository**. When you obtain a CPython build for an
Apple platform, it will have already been linked using these libraries.

If you *do* need to link against these libraries for some reason, you can use
the pre-compiled versions that are published on the `Github releases page
<https://github.com/beeware/cpython-apple-source-deps/releases>`__. You don't
need to compile them yourself.

However, if you *do* need to compile your own version for some reason:

* Clone this repository
* Create a Python 3 virtual environment
* Obtain the Android Command line tools, and set the `ANDROID_HOME` environment
  variable
* Ensure that you have a Java SDK installed, and either `JAVA_HOME` is set, or
  `javac` is available in your path.
* Ensure you have XCode installed, with the macOS and iOS developer kits
  installed
* In the root directory, run `python -m build-dep <library name> --host <host>`.

For example, `python -m build-dep bzip2 --host universal2-apple-darwin` will compile
a Universal2 build of `bzip2` for macOS. You can optionally pass in `--version` to
build a specific version, or `--build` to apply a build identifier.

This should:

1. Download the original source packages
2. Patch them as required for compatibility with the selected OS
3. Build the libraries for the selected OS and architecture
4. Package a tarball containing build products.

The resulting artefacts will be packaged as ``.tar.gz`` files in the ``dist``
folder.
