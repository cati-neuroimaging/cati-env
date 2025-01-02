# soma-dev preliminary specifications

Soma-dev is a project containing all what is necessary to setup a development environment for BrainVISA projects. There are several version of a development environement according to the source git branches or tag used (e.g. master or release) and to the dependencies (e.g. Qt5 vs Qt6). A single instance of a development environment (i.e. a build directory) is setup by choosing, installing and using a soma-dev instance. This document present vert preliminary specification of what is a soma-dev instance an how to use it.

# What is a soma-dev instance

A soma-dev instance is a branch or a tag of this project.
A soma-dev instance contains:
- A version that identify the content of the environement. This should be the name of the branch of the git sources. The following names will be used:
    - *0.0*: corresponds to the main development environement. Uses git default branches (usualy master or main) and "stable" dependencies (Qt5, Capsul 2)
    - *0.1*: development environment to test capsul 3
    - *6.0.0*: first conda-based release of BrainVISA
- A list of packages that can be built using this environement. Each package is associated with a single git URL pointing to the main brainvisa-cmake component of the package. The recipe file for that package is stored in this main component sources (in `soma-dev/soma-recipe.yaml`). This file contains information about other brainvisa-cmake components that are also part of the package.
- A pixi.toml script containing common development dependencies.
- A default configuration for brainvisa-cmake (i.e. a `conf/bv_maker.cfg` file)
- An activation script that makes sure that brainvisa-cmake sources and main components sources are downloaded and ready to use
- Python compatible data containing informations about packages that had been released using this soma-dev branch. In this data each package is associated to the git changeset of each brainvisa component used to build it. This information allows two things:
  - To setup a development environment corresponding to a precise release version, using exactly the same sources
  - To identify the projects that have changed when producing new packages 

# How to use a soma-dev instance ?

A soma-dev instance is created by cloning https://gitbub.com/brainvisa/soma-dev using the appropriate branch. The sources of the project contains a Pixi configuration file to setup a ready to use brainvisa-cmake. One has just to run `pixi shell` to install the environment. Customization can be done by editing appropriate files such as `conf/bv_makeg.cfg`.

# soma-dev: a new command in branvisa-cmake

Modification of a soma-dev instance is done by a command located in brainvisa-cmake project: soma-dev. This command replaces bv_maker. It is a wrapper around some of its subcommands (info, sources, status, configure, build, doc) and is also provides new subcommands:
- *update*: performs *sources* subcommand then pull the sources of the soma-dev instance and update the Pixi dependencies according to the content of all the packages defined in `$PIXI_PROJECT_ROOT/src/*/soma-dev/soma-recipe.yaml`. Thus it updates the development environment dependencies according to the changes in each project.
- *version-plan*: create a plan file `$PIXI_PROJECT_ROOT/plan/actions.yaml` that contains instruction to update version files (`info.py` or `project_info.cmake`) for all projects that have changed since the last release (taking binary dependencies into account).
- *packaging-plan*: create a plan file (`$PIXI_PROJECT_ROOT/plan/actions.yaml`) that contains instructions to create and publish (i.e. copy to `/drf/neuro-forge/public`) packages for all projects that have changes since the last release (taking binary dependencies into account)
- *apply-plan*: execute instructions contained in the plan file `$PIXI_PROJECT_ROOT/plan/actions.yaml`.
- *graphviz*: produces a dot file packages hierarchy.
