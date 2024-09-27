import argparse
import multiprocessing
import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import urlparse

ROOT_PATH = Path(__file__).parent


def download(url, download_path: Path):
    """Download a url, storing the file in the provided path.

    If the archive already exists in the download path, it will not be downloaded again.

    :param url: The URL of the archive file to download.
    :param download_path: The path to a folder that will contain the downloaded archive.
    :returns: The path to the archive.
    """
    filename = Path(urlparse(url).path).name
    archive_path = download_path / filename

    if archive_path.is_file():
        print(f"Using existing archive {archive_path}")
    else:
        print(f"Downloading {url}...")
        subprocess.run(
            [
                "curl",
                "--disable",
                "--fail",
                "--location",
                "--create-dirs",
                "--progress-bar",
                "-o",
                archive_path,
                url
            ]
        )

    return archive_path


def update_env(env, update):
    """Add additional keys to the environment.

    Any value in ``update`` that is defined as a string will be added to the
    enviroment, after formatting the key with the existing values in the
    environment.

    :param env: The current environment dictionary
    :param update: A dictionary of new values to add to the environment.
    """
    for key, value in update.items():
        if isinstance(value, str):
            if key in ["CFLAGS", "LDFLAGS"]:
                if key in env:
                    env[key] += f" {value.format(**env)}"
                else:
                    env[key] = value.format(**env)
            else:
                env[key] = value.format(**env)


def build(host, libname, version, build):
    """Build a library version for a host.

    :param host: The compiler triple for the host.
    :param libname: The name of the library to build.
    :param version: The version of the library to build.
    :param build: The build number."""
    config_filename = ROOT_PATH / libname / "config.toml"
    with config_filename.open("rb") as f:
        config = tomllib.load(f)

    if version is None:
        version = config["version"]

    print(f"Build {libname} v{version} build {build} for {host}")

    archive_path = download(
        config["download_url"].format(version=version),
        ROOT_PATH / "downloads",
    )

    print()
    if host is None:
        print("No host specified; source has been downloaded but not built.")
    else:
        BUILD_PATH = ROOT_PATH / "build" / host / f"{libname}-{version}"
        INSTALL_PATH = ROOT_PATH / "install" / host / libname
        DIST_PATH = ROOT_PATH / "dist"

        if BUILD_PATH.exists():
            print(f"Removing old build path {BUILD_PATH}")
            shutil.rmtree(BUILD_PATH)
        if INSTALL_PATH.exists():
            print(f"Removing old install path {BUILD_PATH}")
            shutil.rmtree(INSTALL_PATH)

        print(f"Unpacking {BUILD_PATH.name} into {BUILD_PATH.parent}")
        shutil.unpack_archive(archive_path, BUILD_PATH.parent, filter="data")

        # Add the platform's environment values
        host_filename = ROOT_PATH / "host" / f"{host}.toml"
        with host_filename.open("rb") as f:
            host_config = tomllib.load(f)

        if "-android" in host:
            # Android requires some additional environment configuration
            # and uses the compiler binaries in the ANDROID_HOME directory
            try:
                android_home = Path(os.getenv("ANDROID_HOME"))
            except KeyError:
                print()
                print("ANDROID_HOME not defined")
                return

            # Ensure that the NDK is installed
            ndk_version = host_config['ndk_version']
            print()
            print(f"Ensure NDK {ndk_version} is installed...")
            subprocess.run(
                [android_home / "cmdline-tools/latest/bin/sdkmanager", f"ndk;{ndk_version}"],
                check=True
            )

            # The exact name of the NDK toolchain is platform specific; assume
            # there's only one folder, and select that one.
            ndk_tools_path = ndk_tools_path = [
                p
                for p in (android_home / "ndk" / ndk_version / "toolchains/llvm/prebuilt").glob("*")
                if p.is_dir()
            ][0]

            env = {
                "ANDROID_HOME": str(android_home)
            }
            tools_path = ndk_tools_path / "bin"
        elif "-ios" in host:
            # iOS uses the compiler shims in the `bin` directory
            if "-simulator" in host:
                sdk = "iphonesimulator"
            else:
                sdk = "iphoneos"

            sdk_root = subprocess.check_output(["xcrun", "--sdk", sdk, "--show-sdk-path"], text=True).strip()
            env = {
                "SDK_ROOT": sdk_root,
            }
            tools_path = str(ROOT_PATH / "bin")

        elif "-darwin" in host:
            # macOS uses the compiler shims in the `bin` directory
            sdk_root = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
            env = {
                "SDK_ROOT": sdk_root,
            }
            tools_path = str(ROOT_PATH / "bin")

        update_env(env, host_config)

        # Add the library's common environment values
        update_env(env, config.get("env", {}))

        # Add the library's platform-specific environment values
        update_env(env, config.get("env", {}).get(host, {}))

        env["PATH"] = os.pathsep.join(
            [
                str(tools_path),
                str(Path.home() / ".cargo/bin"),
                "/usr/bin",
                "/bin",
                "/usr/sbin",
                "/sbin",
                "/Library/Apple/usr/bin",
            ]
        )
        env["PREFIX"] = str(INSTALL_PATH)
        env["CPU_COUNT"] = str(multiprocessing.cpu_count())

        print()
        print("Build environment:")
        for key, value in env.items():
            print(f'export {key}="{value}"')
        print()
        print("Building...")
        try:
            subprocess.run(
                [ROOT_PATH / libname / "build.sh"],
                cwd=BUILD_PATH,
                env=env,
                check=True,
            )
        except subprocess.CalledProcessError:
            print()
            print("*** BUILD FAILED ***")
            return
        print("Build done.")

        print()
        print("Clean up installed directory...")
        for path in ["bin", "man"]:
            if (INSTALL_PATH / path).exists():
                print(f" - Purging {path}")
                shutil.rmtree(INSTALL_PATH / path)
        print("done.")

        for path in INSTALL_PATH.glob("**/*"):
            if path.is_symlink():
                target = path.resolve().relative_to(path.parent)
                print(f" - Rewriting symlink for {target}")
                # Installed symlinks may be absolute.
                # Replace with relative symlinks
                path.unlink()
                path.symlink_to(target)

        print()
        print("Packaging archive...", end="", flush=True)
        shutil.make_archive(
            DIST_PATH / f"{libname}-{version}-{build}-{host}",
            format="gztar",
            root_dir=INSTALL_PATH,
        )
        print("done.")


if __name__ == "__main__":
    android_hosts = [
        "arm-linux-androideabi",
        "aarch64-linux-android",
        "i686-linux-android",
        "x86_64-linux-android",
    ]

    ios_hosts = [
        "arm64-apple-ios",
        "arm64-apple-ios-simulator",
        "x86_64-apple-ios-simulator",
    ]

    macos_hosts = [
        "universal2-apple-darwin",
    ]

    parser = argparse.ArgumentParser(prog="build-dep", description="Build binary dependencies used by CPython.",)
    parser.add_argument("--build", default="0")
    parser.add_argument("--host", choices=android_hosts + ios_hosts + macos_hosts + ["android", "iOS", "macOS", "all"])
    parser.add_argument("--version")
    parser.add_argument("libname")

    args = parser.parse_args()
    if args.host == "all":
        hosts = android_hosts + ios_hosts + macos_hosts
    elif args.host == "android":
        hosts = android_hosts
    elif args.host == "iOS":
        hosts = ios_hosts
    elif args.host == "macOS":
        hosts = macos_hosts
    else:
        hosts = [args.host]

    for host in hosts:
        if len(hosts) > 1:
            print("=" * 80)
        build(host=host, libname=args.libname, version=args.version, build=args.build)
