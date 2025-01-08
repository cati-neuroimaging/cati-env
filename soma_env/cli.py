import copy
import fnmatch
import itertools
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import types

import fire
import git
import yaml

from .defaults import default_publication_directory
from .recipes import sorted_recipies, find_soma_env_packages, read_recipes
from . import plan as plan_module


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

    def version_plan(
        self,
        publication_directory: str = default_publication_directory,
        packages: str = "*",
        force: bool = False,
    ):
        if not publication_directory or publication_directory.lower() == "none":
            publication_directory = None
        else:
            publication_directory = pathlib.Path(publication_directory).absolute()
        if publication_directory is not None and not publication_directory.exists():
            raise RuntimeError(
                f"Publication directory {publication_directory} does not exist"
            )

        selector = re.compile("|".join(f"(?:{fnmatch.translate(i)})" for i in packages))

        plan_dir = self.soma_root / "plan"

        # Check if a plan file already exists and can be erased
        if not force:
            actions_file = plan_dir / "actions.yaml"
            if actions_file.exists():
                with open(actions_file) as f:
                    actions = yaml.safe_load(f)
                if any(action.get("status") == "success" for action in actions):
                    raise RuntimeError(
                        f"A plan already exists in {plan_dir} and was used. "
                        "Erase it or use --force option"
                    )

        # Erase existing plan
        if plan_dir.exists():
            print(f"Erasing existing plan: {plan_dir}")
            shutil.rmtree(plan_dir)
        plan_dir.mkdir()

        # Read environment version
        with open(self.soma_root / "conf" / "soma-env.json") as f:
            environment_version = json.load(f)["version"]

        # Get the release history for selected environment (e.g.
        # environment="6.0") from the publication directory.
        # The release history is located in the
        # f"soma-env-{environment_version}.yaml" file and contains a dict
        # with the following structure:
        #    "soma-env": for each version of soma-env package, contain a dict
        #        associating packages with their version at the time of soma-env
        #        release.
        #    "packages": for each package, contains a dict with all published
        #        versions and, for each version, the brainvisa-cmake components
        #        associated to their git changeset.
        release_history = {"soma-env": {}, "packages": {}}
        last_published_soma_env_version = None
        if publication_directory is not None:
            release_history_file = (
                publication_directory / f"soma-env-{environment_version}.json"
            )
            if release_history_file.exists():
                with open(release_history_file) as f:
                    release_history = json.load(f)
                last_published_soma_env_version = list(
                    release_history["soma-env"].keys()
                )[-1]
                print(f"Release history file: {release_history_file}")
            else:
                print(f"WARNING: {release_history_file} does not exist")

        actions = []
        commit_actions = []

        for recipe in read_recipes(self.soma_root):
            package = recipe["package"]["name"]
            if not selector.match(package):
                print(f"Package {package} excluded from selection")
                continue
            components = list(recipe["soma-env"].get("components", {}).keys())
            if components:
                # Parse components and do the following:
                #  - put error messages in src_errors if source trees are not clean
                #  - Get current git changeset of each component source tree in
                #    changesets
                #  - Add package to selected_packages if any component has changed
                #    since the last release
                changesets = {}
                for component in components:
                    src = self.soma_root / "src" / component
                    repo = git.Repo(src)
                    if repo.is_dirty():
                        print(f"WARNING: repository {src} contains uncomited files")
                    elif repo.untracked_files:
                        print(f"WARNING: repository {src} has local modifications")
                    changesets[component] = str(repo.head.commit)

                latest_changesets = None
                latest_release_version = None
                if last_published_soma_env_version is not None:
                    latest_release_version = release_history["soma-env"][
                        last_published_soma_env_version
                    ].get(package)
                    latest_changesets = (
                        release_history["packages"]
                        .get(package)
                        .get(latest_release_version)
                    )
                if not latest_changesets:
                    print(f"Package {package} not found in release history")
                elif changesets != latest_changesets:
                    print(f"Package {package} modified since last release")
                    if recipe["package"]["version"] == latest_release_version:
                        package_version = tuple(
                            int(i) for i in recipe["package"]["version"].split(".")
                        )
                        new_version = package_version[:-1] + (package_version[-1] + 1,)
                        new_version = ".".join(str(i) for i in new_version)
                        print(
                            f"Set {package} version from {latest_release_version} to {new_version}"
                        )
                        # Find file to change
                        src = next(iter(recipe["soma-env"]["components"].values()))
                        file = src / "pyproject.toml"
                        if file.exists():
                            version_regexps = (
                                re.compile(
                                    r'(\bversion\s*=\s*")([0-9]+)(\.[0-9]+\.[0-9]+")'
                                ),
                                re.compile(
                                    r'(\bversion\s*=\s*"[0-9]+\.)([0-9]+)(\.[0-9]+")'
                                ),
                                re.compile(
                                    r'(\bversion\s*=\s*"[0-9]+\.[0-9]+\.)([0-9]+)(")'
                                ),
                            )
                        else:
                            file = src / "project_info.cmake"
                            if file.exists():
                                version_regexps = (
                                    re.compile(
                                        r"(\bset\s*\(\s*BRAINVISA_PACKAGE_VERSION_MAJOR\s*)"
                                        r"([0-9]+)(\s*\))",
                                        re.IGNORECASE,
                                    ),
                                    re.compile(
                                        r"(\bset\s*\(\s*BRAINVISA_PACKAGE_VERSION_MINOR\s*)"
                                        r"([0-9]+)(\s*\))",
                                        re.IGNORECASE,
                                    ),
                                    re.compile(
                                        r"(\bset\s*\(\s*BRAINVISA_PACKAGE_VERSION_PATCH\s*)"
                                        r"([0-9]+)(\s*\))",
                                        re.IGNORECASE,
                                    ),
                                )
                            else:
                                version_regexps = (
                                    re.compile(r"(\bversion_major\s*=\s*)([0-9]+)(\b)"),
                                    re.compile(r"(\bversion_minor\s*=\s*)([0-9]+)(\b)"),
                                    re.compile(r"(\bversion_micro\s*=\s*)([0-9]+)(\b)"),
                                )
                                files = list(
                                    itertools.chain(
                                        src.glob("info.py"),
                                        src.glob("*/info.py"),
                                        src.glob("python/*/info.py"),
                                    )
                                )
                            if not files:
                                raise RuntimeError(
                                    f"Cannot find component version file (info.py or project_info.cmake) in {src}"
                                )
                            file = files[0]
                        with open(file) as f:
                            file_contents = f.read()
                        for regex, version_component in zip(
                            version_regexps, new_version.split(".")
                        ):
                            file_contents, _ = regex.subn(
                                f"\\g<1>{version_component}\\g<3>", file_contents
                            )
                        print(
                            f"Create action to modify {file} to set {package} version from {latest_release_version} to {new_version}"
                        )
                        actions.append(
                            {
                                "action": "modify_file",
                                "kwargs": {
                                    "file": str(file),
                                    "file_contents": file_contents,
                                },
                            }
                        )
                        commit_actions.append(
                            {
                                "action": "git_commit",
                                "kwargs": {
                                    "repo": str(src),
                                    "modified": [str(file)],
                                    "message": f"Set package {package} from version {latest_release_version} to version {new_version}",
                                },
                            }
                        )

                else:
                    print(f"No change detected in package {package}")

        if commit_actions:
            actions.extend(commit_actions)
            actions.append({"action": "rebuild"})

        with open(plan_dir / "actions.yaml", "w") as f:
            yaml.safe_dump(
                actions,
                f,
            )

    def packaging_plan(
        self,
        publication_directory: str = default_publication_directory,
        packages: str = "*",
        force: bool = False,
        test: bool = False,
    ):
        if not publication_directory or publication_directory.lower() == "none":
            publication_directory = None
        else:
            publication_directory = pathlib.Path(publication_directory).absolute()
        if publication_directory is not None and not publication_directory.exists():
            raise RuntimeError(
                f"Publication directory {publication_directory} does not exist"
            )

        selector = re.compile("|".join(f"(?:{fnmatch.translate(i)})" for i in packages))

        plan_dir = self.soma_root / "plan"

        # Check if a plan file already exists and can be erased
        if not force:
            actions_file = plan_dir / "actions.yaml"
            if actions_file.exists():
                with open(actions_file) as f:
                    actions = yaml.safe_load(f)
                if any(action.get("status") == "success" for action in actions):
                    raise RuntimeError(
                        f"A plan already exists in {plan_dir} and was used. "
                        "Erase it or use --force option"
                    )

        # Erase existing plan
        if plan_dir.exists():
            print(f"Erasing existing plan: {plan_dir}")
            shutil.rmtree(plan_dir)
        plan_dir.mkdir()

        # Read environment version
        with open(self.soma_root / "conf" / "soma-env.json") as f:
            environment_version = json.load(f)["version"]
        development_environment = environment_version.startswith("0.")

        # Get the release history for selected environment (e.g.
        # environment="6.0") from the publication directory.
        # The release history is located in the
        # f"soma-env-{environment_version}.yaml" file and contains a dict
        # with the following structure:
        #    "soma-env": for each version of soma-env package, contain a dict
        #        associating packages with their version at the time of soma-env
        #        release.
        #    "packages": for each package, contains a dict with all published
        #        versions and, for each version, the brainvisa-cmake components
        #        associated to their git changeset.
        release_history = {"soma-env": {}, "packages": {}}
        last_published_soma_env_version = None
        if publication_directory is not None:
            release_history_file = (
                publication_directory / f"soma-env-{environment_version}.json"
            )
            if release_history_file.exists():
                with open(release_history_file) as f:
                    release_history = json.load(f)
                last_published_soma_env_version = list(
                    release_history["soma-env"].keys()
                )[-1]
                print(f"Release history file: {release_history_file}")
            else:
                print(f"WARNING: {release_history_file} does not exist")

        # Set the new soma-env full version by incrementing last published version patch
        # number or setting it to 0
        if last_published_soma_env_version:
            # Increment patch number
            version, patch = last_published_soma_env_version.rsplit(".", 1)
            patch = int(patch) + 1
            future_published_soma_env_version = f"{version}.{patch}"
            release_history["soma-env"][future_published_soma_env_version] = (
                copy.deepcopy(
                    release_history["soma-env"][last_published_soma_env_version]
                )
            )
        else:
            future_published_soma_env_version = f"{environment_version}.0"
            release_history["soma-env"][future_published_soma_env_version] = {}

        # Next environment version is used to build dependencies strings
        # for components:
        #   >={environment_version},<{next_environment_version}
        next_environment_version = environment_version.split(".")
        next_environment_version[-1] = str(int(next_environment_version[-1]) + 1)
        next_environment_version = ".".join(next_environment_version)

        # Build string for new packages
        build_string = f"py{sys.version_info[0]}{sys.version_info[1]}"

        # List of actions stored in the plan file
        actions = []

        recipes = {}
        selected_packages = set()
        # Get ordered selection of recipes. Order is based on package
        # dependencies. Recipes are selected according to user selection and
        # modification since last packaging
        for recipe in sorted_recipies(self.soma_root):
            package = recipe["package"]["name"]
            if not selector.match(package):
                print(f"Package {package} excluded from selection")
                continue
            components = list(recipe["soma-env"].get("components", {}).keys())
            if components:
                # Parse components and do the following:
                #  - put error messages in src_errors if source trees are not clean
                #  - Get current git changeset of each component source tree in
                #    changesets
                #  - Add package to selected_packages if any component has changed
                #    since the last release
                src_errors = []
                changesets = {}
                for component in components:
                    src = self.soma_root / "src" / component
                    repo = git.Repo(src)
                    if repo.is_dirty():
                        src_errors.append(f"repository {src} contains uncomited files")
                    elif repo.untracked_files:
                        src_errors.append(f"repository {src} has local modifications")
                    changesets[component] = str(repo.head.commit)

                latest_changesets = None
                if last_published_soma_env_version is not None:

                    latest_changesets = (
                        release_history["packages"]
                        .get(package)
                        .get(
                            release_history["soma-env"][
                                last_published_soma_env_version
                            ].get(package)
                        )
                    )
                if not latest_changesets:
                    print(
                        f"Select {package} because no source changesets was found in release history"
                    )
                    selected_packages.add(package)
                elif changesets != latest_changesets:
                    changes = sorted(i for i in changesets if changesets[i] != latest_changesets.get(i))
                    print(
                        f"Select {package} for building because some source has changed (in {' '.join(changes)}) since latest release"
                    )
                    selected_packages.add(package)
                else:
                    print(f"No change detected in package {package}")

                # Write build section in recipe

                recipe.setdefault("build", {})["string"] = build_string
                recipe["build"]["script"] = "\n".join(
                    (
                        f"cd '{self.soma_root}'",
                        f"pixi run --manifest-path='{self.soma_root}/pyproject.toml' bash << END",
                        "set -x",
                        'cd "\\$SOMA_ROOT/build"',
                        'export BRAINVISA_INSTALL_PREFIX="$PREFIX"',
                        f"for component in {' '.join(components)}; do",
                        "  make install-\\${component}",
                        "  make install-\\${component}-dev",
                        "  make install-\\${component}-usrdoc",
                        "  make install-\\${component}-devdoc",
                        "done",
                        "END",
                    )
                )
                # Save information in recipe because we do not know yet
                # if package will be selected for building. It will be known
                # later when dependencies are resolved.
                recipe["soma-env"]["src_errors"] = src_errors
                recipe["soma-env"]["changesets"] = changesets
            elif recipe["soma-env"]["type"] == "virtual":
                raise NotImplementedError(
                    "packaging of virtual packages not implemented"
                )
                recipe["package"]["version"] = environment_version
                recipe.setdefault("build", {})["string"] = build_info["build_string"]
                print(
                    f"Select virtual package {package} {environment_version} for building"
                )
                selected_packages.add(package)
            else:
                raise Exception(
                    f"Invalid recipe for {package} (bad type or no component defined)"
                )
            recipes[package] = recipe

        if not selected_packages:
            print("Nothing to do.")
            return
        
        # Select new packages that are compiled and depend on, at least, one selected compiled package
        selection_modified = True
        while selection_modified:
            selection_modified = False
            for package, recipe in recipes.items():
                if package in selected_packages:
                    continue
                if recipe["soma-env"]["type"] == "compiled":
                    for other_package in recipe["soma-env"].get(
                        "internal-dependencies", []
                    ):
                        if recipes[other_package]["soma-env"]["type"] != "compiled":
                            continue
                        if other_package in selected_packages:
                            print(
                                f"Select {package} because it is binary dependent on {other_package} which is selected"
                            )
                            selected_packages.add(package)
                            selection_modified = True

    
        # Generate rattler-build recipe and action for soma-env package
        print(f"Generate recipe for soma-env {future_published_soma_env_version}")
        (plan_dir / "recipes" / "soma-env").mkdir(exist_ok=True, parents=True)
        with open(plan_dir / "recipes" / "soma-env" / "recipe.yaml", "w") as f:
            yaml.safe_dump(
                {
                    "package": {
                        "name": "soma-env",
                        "version": future_published_soma_env_version,
                    },
                    "build": {
                        "string": f"py{sys.version_info[0]}{sys.version_info[1]}",
                        "script": (
                            "mkdir --parents $PREFIX/share/soma\n"
                            f"echo '{future_published_soma_env_version}' > soma-env.version"
                        ),
                    },
                    "requirements": {
                        "run": [f"python=={sys.version_info[0]}.{sys.version_info[1]}"]
                    },
                },
                f,
            )

        # Generate rattler-build recipe and actions for selected packages
        package_actions = []
        for package, recipe in recipes.items():
            if package not in selected_packages:
                continue
            if development_environment:
                recipe["package"]["version"] = future_published_soma_env_version
            print(f"Generate recipe for {package} {recipe['package']['version']}")
            if not force:
                src_errors = recipe["soma-env"].get("src_errors")
                if src_errors:
                    raise Exception(
                        f"Cannot build {package} because {', '.join(src_errors)}."
                    )
            internal_dependencies = recipe["soma-env"].get("internal-dependencies", [])
            if internal_dependencies:
                for dpackage in internal_dependencies:
                    d = f"{dpackage}>={recipes[dpackage]['package']['version']}"
                    recipe.setdefault("requirements", {}).setdefault("run", []).append(
                        d
                    )

            changesets = recipe["soma-env"].get("changesets")

            # Add dependency to soma-env package
            recipe["requirements"]["run"].append(
                f"soma-env>={future_published_soma_env_version},<{next_environment_version}"
            )

            # Remove soma-env specific data from recipe
            recipe.pop("soma-env", None)

            (plan_dir / "recipes" / package).mkdir(exist_ok=True, parents=True)

            with open(plan_dir / "recipes" / package / "recipe.yaml", "w") as f:
                yaml.safe_dump(recipe, f)

            package_actions.append(
                {
                    "action": "create_package",
                    "args": [package],
                    "kwargs": {"test": test},
                }
            )

            release_history["soma-env"][future_published_soma_env_version][package] = (
                recipe["package"]["version"]
            )
            release_history["packages"].setdefault(package, {})[
                recipe["package"]["version"]
            ] = changesets

        # Add an action to assess that compilation was successfully done
        actions.append({"action": "check_build_status"})

        actions.append(
            {
                "action": "create_package",
                "args": ["soma-env"],
                "kwargs": {"test": False},
            }
        )

        actions.extend(package_actions)
        packages_dir = self.soma_root / "plan" / "packages"
        if publication_directory is not None:
            actions.append(
                {
                    "action": "publish",
                    "kwargs": {
                        "environment": environment_version,
                        "packages_dir": str(packages_dir),
                        "packages": ["soma-env"] + list(selected_packages),
                        "release_history": release_history,
                        "publication_dir": str(publication_directory),
                    },
                }
            )

        with open(plan_dir / "actions.yaml", "w") as f:
            yaml.safe_dump(
                actions,
                f,
            )

    def apply_plan(self):
        with open(self.soma_root / "plan" / "actions.yaml") as f:
            actions = yaml.safe_load(f)
        context = types.SimpleNamespace()
        context.soma_root = self.soma_root
        for action in actions:
            if action.get("status") != "success":
                getattr(plan_module, action["action"])(
                    context, *action.get("args", []), **action.get("kwargs", {})
                )
                action["status"] = "success"
                with open(self.soma_root / "plan" / "actions.yaml", "w") as f:
                    yaml.safe_dump(actions, f)

    def graphviz(self, packages: str = "*", conda_forge=False, versions=False):
        """Output a dot file for selected packages (or for all known packages by default)"""
        selector = re.compile("|".join(f"(?:{fnmatch.translate(i)})" for i in packages))
        neuro_forge_packages = set()
        conda_forge_packages = set()
        linked = set()
        print("digraph {")
        print("  node [shape=box, color=black, style=filled]")
        recipes = {
            recipe["package"]["name"]: recipe
            for recipe in sorted_recipies(self.soma_root)
        }
        selected_recipes = set()
        stack = [i for i in recipes if selector.match(i)]
        while stack:
            package = stack.pop(0)
            selected_recipes.add(package)
            recipe = recipes[package]
            stack.extend(
                dependency
                for dependency in recipe["soma-env"].get("internal-dependencies", [])
                if dependency not in selected_recipes
            )

        all_soma_env_packages = set(find_soma_env_packages(self.soma_root))
        for package in selected_recipes:
            recipe = recipes[package]
            if versions:
                version = recipe["package"]["version"]
                label = f'"{package} ({version})"'
            else:
                label = f'"{package}"'
            if recipe["soma-env"]["type"] == "interpreted":
                print(f'  "{package}" [label={label},fillcolor="aquamarine2"]')
            elif recipe["soma-env"]["type"] == "compiled":
                print(
                    f'  "{package}" [label={label},fillcolor="darkgreen",fontcolor=white]'
                )
            elif recipe["soma-env"]["type"] == "virtual":
                print(f'  "{package}" [label={label},fillcolor="powderblue"]')
            else:
                print(f'  "{package}" [fillcolor="bisque"]')
            for dependency in recipe["soma-env"].get("internal-dependencies", []):
                if (package, dependency) not in linked:
                    print(f'  "{package}" -> "{dependency}"')
                    linked.add((package, dependency))
            for dependency in recipe.get("requirements", {}).get("run", []):
                if dependency in all_soma_env_packages:
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
