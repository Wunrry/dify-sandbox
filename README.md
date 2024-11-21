# DIFY-SANDBOX-PY
[English](README.md) | [中文](README_CN.md)

This is a code executor for Dify that is compatible with official sandbox API calls and dependency installation.

## Purpose
While the official sandbox has many permission-related settings and offers a better sandboxing solution, in personal use cases where Dify code nodes are entirely self-edited, code injection risks are minimal. This project aims to provide broader permissions and support for more dependency packages (such as numpy>2.0, matplotlib), while reducing confusing error messages. This code was developed by referencing the official sandbox's API call examples.

## Usage
In the official docker-compose.yaml, locate the sandbox image section and replace it with:
```
  sandbox:
    # image: langgenius/dify-sandbox:0.2.10
    image: svcvit/dify-sandbox-py:0.1.0
```

If you prefer to build the image yourself for security reasons, you can download this repository and run:
```
docker build -t dify-sandbox-py:local .
```
Then modify the sandbox image in `docker-compose.yaml` to use `dify-sandbox-py:local`

## Notes
- This image only supports Python code, with Python updated to version 3.12
- JavaScript is not supported
- Network access restrictions have been removed, network access is enabled by default
- Third-party dependency installation works the same as the official version - place required dependencies in `/docker/volumes/sandbox/dependencies/python-requirements.txt` and restart the sandbox
- The image only includes FastAPI-related dependencies; any additional dependencies you need must be added to python-requirements.txt