# DIFY-SANDBOX-PY
[English](README.md) | [中文](README_CN.md)

这是一个供 Dify 使用的代码执行器，兼容官方sandbox的API调用以及依赖安装。
- 支持 Python3.12
- 支持 Node.js 20

## 目的
因为官方sandbox有很多关于权限的设置，那是一个更好的沙盒方案，但是个人实际使用过程中，Dify的代码节点完全是个人编辑，所以也不存在代码注入风险，希望有更大的权限，安装更多依赖包例如numpy>2.0，matplotlib，scikit-learn 减少一些看不懂的报错，因此参考官方sandbox的API调用示例，开发了本代码。

## 用法
在官方 docker-compose.yaml 中，找到 sandbox 的 image 部分内容，替换镜像即可。
```
  sandbox:
    # image: langgenius/dify-sandbox:0.2.10
    image: svcvit/dify-sandbox-py:0.1.2
    # image: dockerpull.org/svcvit/dify-sandbox-py:0.1.2  #如果你是国内用户，用这个也可以，如果失败，多拉两次
```

如果你不放心，希望自己打包镜像，你可以下载这个仓库，运行下面的代码打包
```
docker build -t dify-sandbox-py:local .
```
然后修改`docker-compose.yaml`里面sandbox为上面的`dify-sandbox-py:local`即可

## 截图
Python的支持
![](/images/Xnip2024-11-25_11-30-12.jpg)
nodejs的支持
![](/images/Xnip2024-11-25_11-31-01.jpg)
docker容器的日志
![](/images/Xnip2024-12-04_10-15-18.jpg)

## 说明
- 去掉了网络访问的控制，默认就支持访问网络
- 使用UV作为依赖管理，安装依赖速度更快，重启可以毫秒级安装依赖。
- 第三方依赖安装与官方一致，将需要的依赖放入`/docker/volumes/sandbox/dependencies/python-requirements.txt`，重启sandbox即可。
- 镜像只有fastapi相关的依赖，任何你需要的依赖，需要自己加到python-requirements.txt中。




