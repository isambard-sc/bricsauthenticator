# mappingauthenticator

JupyterHub `Authenticator` backed by a simple username:password mapping

## Install

The package uses a ["src layout"][layouts-python-packaging-user-guide]. It should be installed to run or develop the code.

[layouts-python-packaging-user-guide]: https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/

It is recommended to first create a virtual environment

```shell
python -m venv --upgrade-deps /path/to/my-venv
```

then install the package into the virtual environment.

### Install directly from the GitHub repository

```shell
/path/to/my-venv/bin/python -m pip install "mappingauthenticator @ git+https://github.com/isambard-sc/mappingauthenticator.git"
```

### Install from local clone of repository

Clone the repository

```shell
git clone https://github.com/isambard-sc/mappingauthenticator.git
```

Then install into the virtual environment using the path to the cloned repository

```shell
/path/to/my-venv/bin/python -m pip install /path/to/mappingauthenticator
```

An [editable install][editable-installs-pip-docs] is useful when developing. This adds files in the source directory to the Python import path, so edits to the source code are reflected in the installed package.

[editable-installs-pip-docs]: https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs

```shell
/path/to/my-venv/bin/python -m pip install -e /path/to/mappingauthenticator
```

> [!NOTE]
> Edits to project metadata will still require reinstallation of the package.

### Install from built distribution

Clone the repository

```shell
git clone https://github.com/isambard-sc/mappingauthenticator.git
```

Build the distribution (requires [`build`][pypa-build-docs])

[pypa-build-docs]: https://build.pypa.io

```shell
python -m build /path/to/mappingauthenticator
```

Install from the sdist or wheel placed in the `dist/` directory

```shell
/path/to/my-venv/bin/python -m pip install /path/to/mappingauthenticator/dist/mappingauthenticator-{version}.tar.gz
```

```shell
/path/to/my-venv/bin/python -m pip install /path/to/mappingauthenticator/dist/mappingauthenticator-{version}-py3-none-any.whl
```

### Install with development dependencies

Use the `[dev]` optional dependency to install development tools (linting, formatting, testing etc.) alongside the `mappingauthenticator` package.

This is useful in combination with an editable install from a local copy of the repository. The local copy can then be worked with using the development tools.

```shell
/path/to/my-venv/bin/python -m pip install -e '/path/to/mappingauthenticator[dev]'
```

## Usage

<!-- TODO -->

### JupyterHub configuration

<!-- TODO -->

## Development

It is recommended to develop in a virtual environment, with [an editable install of the package, and development tools installed](#install-with-development-dependencies).

### Documentation
  
Source documentation should be done using docstrings (see e.g. [PEP-257][pep-257]) using [Sphinx style convention][sphinx-rtd-tutorial-docstrings]

[pep-257]: https://peps.python.org/pep-0257/
[sphinx-rtd-tutorial-docstrings]: https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html

### Lint

Check source files for issues (no modification):

```shell
make lint
```

### Format

In-place modification of source files to fix issues:

```shell
make format
```

### Test

Run tests for package:

```shell
make test
```
