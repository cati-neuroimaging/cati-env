import fnmatch
import os
import pathlib
import re
import subprocess

import fire

from .recipes import sorted_recipies, find_soma_dev_packages


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

    def graphviz(self, packages: str = "*", conda_forge=False):
        """Output a dot file for selected packages (or for all known packages by default)"""
        selector = re.compile("|".join(f"(?:{fnmatch.translate(i)})" for i in packages))
        neuro_forge_packages = set()
        conda_forge_packages = set()
        linked = set()
        print("digraph {")
        print("  node [shape=box, color=black, style=filled]")
        recipes ={recipe["package"]["name"]: recipe for recipe in sorted_recipies()}
        selected_recipes = set()
        stack = [i for i in recipes if selector.match(i)]
        while stack:
            package = stack.pop(0)
            selected_recipes.add(package)
            recipe = recipes[package]
            stack.extend(
                dependency
                for dependency in recipe["soma-dev"].get("internal-dependencies", [])
                if dependency not in selected_recipes
            )

        all_soma_dev_packages = set(find_soma_dev_packages())
        for package in selected_recipes:
            recipe = recipes[package]
            if recipe["soma-dev"]["type"] == "interpreted":
                print(f'  "{package}" [fillcolor="aquamarine2"]')
            elif recipe["soma-dev"]["type"] == "compiled":
                print(f'  "{package}" [fillcolor="darkgreen",fontcolor=white]')
            elif recipe["soma-dev"]["type"] == "virtual":
                print(f'  "{package}" [fillcolor="powderblue"]')
            else:
                print(f'  "{package}" [fillcolor="bisque"]')
            for dependency in recipe["soma-dev"].get("internal-dependencies", []):
                if (package, dependency) not in linked:
                    print(f'  "{package}" -> "{dependency}"')
                    linked.add((package, dependency))
            for dependency in recipe.get("requirements", {}).get("run", []):
                if dependency in all_soma_dev_packages:
                    neuro_forge_packages.add(dependency)
                    print(f'  "{package}" -> "{dependency}"')
                elif conda_forge:
                    conda_forge_packages.add(dependency)
                    print(f'  "{package}" -> "{dependency}"')
        for package in neuro_forge_packages:
            print(f'  "{package}" [fillcolor="bisque"]')
        for package in conda_forge_packages:
            print(f'  "{package}" [fillcolor="aliceblue"]')
        print("}")


def main():
    fire.Fire(Commands)
