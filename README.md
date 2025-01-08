# soma-env

Soma-env is the entry point for the development of projects that depends on soma, the C++/Python ecosystem of BrainVISA suite. BrainVISA team maintain several versions of soma-env. Each version fixes version of software dependencies (e.g. Qt version) as well as git branches of BrainVISA projects. The following soma-env versions are currently supported:

- *0.0*: corresponds to the main development environement. Uses git default branches (usualy master or main) and "stable" dependencies (Qt5, Capsul 2)
- *0.1*: development environment to test capsul 3. Has the same dependencies as 0.0 but uses Capsul 3 specific branches for some projects.
- *6.0*: will be the branch for the first conda-based release of BrainVISA. It has the same dependencies as 0.0 but uses `soma-env-6.0` branches for all BrainVISA projects.

# Prerequisite

soma-env requires [to install Pixi. Pixi](https://pixi.sh/) is a package manager fully compatible with Conda packages ecosystem but, at the time of this writing, much more efficient than Conda.

# Setup a development environment

To setup de development environment ready to use (with a functionnal `bv_maker`) one just need to clone this project (eventually choosing the branch corresponding to a specific version) and run `soma-env update` with `pixi`:

```
git clone https://github.com/brainvisa/soma-env
cd soma-env
pixi run soma-env update
```

# Create neuro-forge packages

Package creation is always done from a soma-env environement activated through Pixi.

## Publication directory

To create packages, `soma-env` needs a publication directory. This directory is a conda repository where new packages will be stored. It must also contains some basic packages that are used as dependencies by some projects. These basic packages are stored in the neuro-forge repository whose reference directory is located in Neurospin (`soma-env` uses this reference directory by default). But it is possible to create a publication directory from scratch using [neuro-forge](https://github.com/neurospin/neuro-forge):

```
git clone https://github.com/neurospin/neuro-forge
cd neuro-forge
# matlab-runtime-9.7 must be build before spm12 package. But neuro-forge doesn't
# manage this dependency. Therefore we start by expicitely building matlab runtime.
pixi run neuro-forge build ~/publication-directory matlab-runtime-9.7
pixi run neuro-forge build ~/publication-directory
```

## Clean sources and compilation

Packaging can only be done if sources are clean (no modified files and all commits pushed) and if `bv_maker` was successfully run with the following steps: `sources`, `configure`, `build` and `doc` (these are the default `bv_maker` steps in soma-env).

## Packaging history

History of the packaging is stored in the publication directory. This history contains the changesets of the git sources used to produce packages. This allows `soma-env` to produce packages only when there is a modification in sources.

## Package version management

For release packages, it is mandatory to increment the version of all the packages that are modified. This must be by changing some components version in sources prior to the packages generation. `soma-env` provides a two step process to do this. First call:

```
soma-env version-plan --publication_directory ~/publication-directory
```

This will identify packages requirering version change according to source modification since the last release. Accordingly, this creates a plan file in `plan/actions.yaml` containing instructions to modify files and commit them. This plan can be checked and modified before it is executed with the following command:

```
soma-env apply-plan
```

## Package creation

Once sources are clean, compilation is done and eventually version changes are managed, packages creation can be done done via `soma-env` command. This is a two step process where the first step is the creation of a packaging plan (that can be checked and/or modified) and then the execution of the plan to create packages, copy them to the publication directory and update the history.

```
soma-env packaging-plan --publication-directory=~/publication-directory
soma-dev apply-plan
```
