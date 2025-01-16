# DIFY-SANDBOX-PY
[English](README.md) | [中文](README_CN.md)

A code executor for Dify that is compatible with the official sandbox API calls and dependency installation.
- Supports Python 3.12
- Supports Node.js 20

## Purpose
While the official sandbox has many permission settings and is a better sandboxing solution, in personal use cases where Dify's code nodes are entirely self-edited, there's no risk of code injection. This project aims to provide broader permissions and support for more dependencies (like numpy>2.0, matplotlib, scikit-learn) to reduce confusing error messages. This code was developed by referencing the official sandbox's API call examples.

## Modify part
Modify the python part as needed, which is more suitable for data analysis. 1. Add the default installation package numpy pandas matplotlib 2. Add the "/v1/sandbox/plot" endpoint to receive json files and return image files. Usage example: You can use the following JSON data to test new API endpoints:
```
{
    "x": [1, 2, 3, 4, 5],
    "y": [10, 20, 25, 30, 40],
    "title": "Sample Plot",
    "xlabel": "X Axis",
    "ylabel": "Y Axis"
}
```
Sending a POST request to the /v1/sandbox/plot endpoint will return an image in PNG format.

## Usage
In the official docker-compose.yaml, locate the sandbox image section and replace it with:
```
  sandbox:
    # image: langgenius/dify-sandbox:0.2.10
    image: svcvit/dify-sandbox-py:0.1.2
```

If you prefer to build the image yourself, you can clone this repository and run:
```
docker build -t dify-sandbox-py:local .
```
Then modify the sandbox image in `docker-compose.yaml` to use `dify-sandbox-py:local`

## Screenshots
Python support
![](/images/Xnip2024-11-25_11-30-12.jpg)
Node.js support
![](/images/Xnip2024-11-25_11-31-01.jpg)
Docker container logs
![](/images/Xnip2024-12-04_10-15-18.jpg)


## Notes
- Network access restrictions have been removed; network access is enabled by default
- Using UV as the dependency manager for faster package installation, allowing millisecond-level dependency installation on restart
- Third-party dependencies can be installed following the official method: simply add required dependencies to `/docker/volumes/sandbox/dependencies/python-requirements.txt` and restart the sandbox
- The image only contains FastAPI-related dependencies. Any additional dependencies you need must be manually added to python-requirements.txt
