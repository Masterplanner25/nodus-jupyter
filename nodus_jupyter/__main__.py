"""Entry point: python -m nodus_jupyter install | run."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile


def _install(user: bool = False, prefix: str | None = None) -> None:
    from jupyter_client.kernelspec import KernelSpecManager

    kernel_json = {
        "argv": [sys.executable, "-m", "nodus_jupyter", "run", "-f", "{connection_file}"],
        "display_name": "Nodus",
        "language": "nodus",
        "codemirror_mode": "python",
    }

    with tempfile.TemporaryDirectory() as td:
        spec_dir = os.path.join(td, "nodus")
        os.makedirs(spec_dir)
        with open(os.path.join(spec_dir, "kernel.json"), "w", encoding="utf-8") as fh:
            json.dump(kernel_json, fh, indent=2)

        ksm = KernelSpecManager()
        dest = ksm.install_kernel_spec(
            spec_dir, "nodus", user=user, prefix=prefix, replace=True
        )

    print(f"Nodus kernel installed to: {dest}")
    print("Start Jupyter and select 'Nodus' from the kernel list.")


def _run(connection_file: str) -> None:
    from ipykernel.kernelapp import IPKernelApp
    from nodus_jupyter.kernel import NodusKernel

    IPKernelApp.launch_instance(kernel_class=NodusKernel, argv=["-f", connection_file])


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m nodus_jupyter")
    sub = parser.add_subparsers(dest="cmd")

    inst = sub.add_parser("install", help="Install the Nodus kernel spec into Jupyter")
    inst.add_argument("--user", action="store_true", help="Install for current user only")
    inst.add_argument("--prefix", default=None, help="Install under this prefix")

    run_p = sub.add_parser("run", help="Launch the kernel (called by Jupyter)")
    run_p.add_argument("-f", dest="connection_file", required=True)

    args = parser.parse_args()

    if args.cmd == "install":
        _install(user=args.user, prefix=args.prefix)
    elif args.cmd == "run":
        _run(args.connection_file)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
