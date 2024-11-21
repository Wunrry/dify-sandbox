# DIFY-SANDBOX-PY
这是一个供 Dify 使用的代码执行器，兼容官方sandbox的API调用以及依赖安装。

## 目的
因为官方sandbox有很多关于权限的设置，那是一个更好的沙盒方案，但是个人实际使用过程中，Dify的代码节点完全是个人编辑，所以也不存在代码注入风险，希望有更大的权限，安装更多依赖包例如numpy>2.0，matplotlib，减少一些看不懂的报错，因此参考官方sandbox的API调用示例，开发了本代码。

## 用法
在官方 docker-compose.yaml 中，找到 sandbox 的 image 部分内容，替换镜像即可。
```
  sandbox:
    # image: langgenius/dify-sandbox:0.2.10
    image: svcvit/dify-sandbox-py:0.1.0
    # image: dockerpull.org/svcvit/dify-sandbox-py:0.1.0  #如果你是国内用户，用这个也可以，如果失败，多拉两次
```

如果你不放心，希望自己打包镜像，你可以下载这个仓库，运行下面的代码打包
```
docker build -t dify-sandbox-py:local .
```
然后修改`docker-compose.yaml`里面sandbox为上面的`dify-sandbox-py:local`即可


## 说明
- 目前这个镜像只支持Python代码，容器更新到 3.12 的Python。
- 只支持Python，JS不支持。
- 去掉了网络访问的控制，默认就支持访问网络
- 第三方依赖安装与官方一致，将需要的依赖放入`/docker/volumes/sandbox/dependencies/python-requirements.txt`，重启sandbox即可。
- 镜像只有fastapi相关的依赖，任何你需要的依赖，需要自己加到python-requirements.txt中。




