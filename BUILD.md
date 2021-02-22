# Build
**Developer note:** This software was packaged for distribution via the Python Package Index (PyPi)
following instructions in https://packaging.python.org/tutorials/packaging-projects
and https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html.

### Windows build and upload
From the project's `distribution` folder:
* venv\Scripts\activate
* python -m pip install --upgrade pip build twine
* python -m build
* twine upload dist/*
    * Enter your username: \_\_token__
    * Enter your password:  (use Edit>Paste from cmdtool window header because Cntl-V doesn't work.
      Right-click might or might not paste the `pypi-****` token correctly.)