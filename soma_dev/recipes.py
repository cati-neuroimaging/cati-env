import os
import pathlib
import yaml

import brainvisa_cmake.brainvisa_projects as brainvisa_projects


def read_recipes():
    """
    Iterate over all recipes files defined in soma-forge.
    """
    soma_root = pathlib.Path(os.environ["SOMA_ROOT"])
    for component_src in (soma_root / "src").iterdir():
        recipe_file = component_src / "soma-dev" / "soma-recipe.yaml"
        if recipe_file.exists():
            with open(recipe_file) as f:
                recipe = yaml.safe_load(f)

                # Set recipe version as component version
                pinfo = brainvisa_projects.read_project_info(component_src)
                if pinfo:
                    project, component, component_version, build_model = pinfo
                    recipe["package"]["version"] = component_version
                else:
                    print(
                        f"WARNING: directory {component_src} does not contain project_info.cmake, python/*/info.py or */info.py file"
                    )
                yield recipe


def selected_recipes(selection=None):
    """
    Iterate over recipes selected in configuration and their dependencies.
    """
    # Read recipes
    recipes = {r["package"]["name"]: r for r in read_recipes()}

    all_packages = set(recipes)

    metapackages = {
        "all": all_packages,
    }
    if not selection:
        selection = ["all"]
    selected_packages = set()
    for s in selection:
        if s.startswith("-"):
            s = s[1:].strip()
            remove = True
        else:
            remove = False
        m = metapackages.get(s)
        if m is not None:
            s = m
        else:
            s = {s}
        if remove:
            selected_packages = selected_packages.difference(s)
        else:
            selected_packages.update(s)

    # Walk over selected packages and dependencies
    stack = list(selected_packages)
    done = set()
    while stack:
        package = stack.pop(0)
        if package in done:
            continue
        recipe = recipes[package]
        yield recipe
        done.add(package)
        dependencies = recipe["soma-dev"].get("internal-dependencies", [])
        stack.extend(i for i in dependencies if i not in done)


def sorted_recipies():
    """
    Iterate over recipes sorted according to their dependencies starting with a
    package without dependency.
    """
    recipes = {r["package"]["name"]: r for r in selected_recipes()}
    ready = set()
    inverted_dependencies = {}
    for package, recipe in recipes.items():
        dependencies = recipe["soma-dev"].get("internal-dependencies", [])
        if not dependencies:
            ready.add(package)
        for dependency in dependencies:
            inverted_dependencies.setdefault(dependency, set()).add(package)

    done = set()
    while ready:
        package = ready.pop()
        yield recipes[package]
        done.add(package)
        for dependent in inverted_dependencies.get(package, []):
            dependencies = recipe.get("internal-dependencies", [])
            if all(d in done for d in dependencies):
                ready.add(dependent)


def find_soma_dev_packages():
    for recipe in read_recipes():
        yield recipe["package"]["name"]
