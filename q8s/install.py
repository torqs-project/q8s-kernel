import json
import os
import sys
import argparse
import pathlib
import shutil

from jupyter_client.kernelspec import KernelSpecManager
from IPython.utils.tempdir import TemporaryDirectory

# from .resources import _ICON_PATH

kernel_json = {
    "argv": [sys.executable, "-m", "q8s", "-f", "{connection_file}"],
    "display_name": "Q8s kernel",
    "language": "python",
}


def install_my_kernel_spec(user=True, prefix=None):
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755)  # Starts off as 700, not user readable
        with open(os.path.join(td, "kernel.json"), "w") as f:
            json.dump(kernel_json, f, sort_keys=True)
        # shutil.copyfile(_ICON_PATH, pathlib.Path(td) / _ICON_PATH.name)
        print("Installing q8s kernel spec")
        KernelSpecManager().install_kernel_spec(td, "q8s", user=user, prefix=prefix)


def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False  # assume not an admin on non-Unix platforms


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Install KernelSpec for Qubernetes Kernel"
    )
    prefix_locations = parser.add_mutually_exclusive_group()

    prefix_locations.add_argument(
        "--user",
        help="Install KernelSpec in user's home directory",
        action="store_true",
    )
    prefix_locations.add_argument(
        "--sys-prefix",
        help="Install KernelSpec in sys.prefix. Useful in conda / virtualenv",
        action="store_true",
        dest="sys_prefix",
    )
    prefix_locations.add_argument(
        "--prefix", help="Install KernelSpec in this prefix", default=None
    )

    args = parser.parse_args(argv)

    user = False
    prefix = None
    if args.sys_prefix:
        prefix = sys.prefix
    elif args.prefix:
        prefix = args.prefix
    elif args.user or not _is_root():
        user = True

    install_my_kernel_spec(user=user, prefix=prefix)


if __name__ == "__main__":
    main()
