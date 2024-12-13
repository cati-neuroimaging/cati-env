import os
import pathlib
import subprocess

import fire
import yaml


class Commands:
    def __init__(self):
        self.soma_root = pathlib.Path(os.environ["SOMA_ROOT"]).absolute()

    def info(self):
        return subprocess.call(["bv_maker", "info"])

    def sources(self):
        return subprocess.call(["bv_maker", "sources"])

    def status(self):
        raise NotImplementedError()

    def configure(self):
        return subprocess.call(["bv_maker", "configure"])

    def build(self):
        return subprocess.call(["bv_maker", "build"])

    def doc(self):
        return subprocess.call(["bv_maker", "doc"])

    def all(self):
        return subprocess.call(["bv_maker"])

    def version_plan(self):
        raise NotImplementedError()

    def packaging_plan(self):
        raise NotImplementedError()

    def apply_plan(self):
        raise NotImplementedError()

    def graphviz(self):
        raise NotImplementedError()


def main():
    fire.Fire(Commands)
