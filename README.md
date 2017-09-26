---
layout:     post
title:      "Docker容器迁移项目实现总结"
subtitle:   "Python实现docker容器C/R"
date:       2017-09-25 13:00:00
author:     "Xu"
header-img: "img/post-bg-2015.jpg"
catalog: true
tags:
    - docker迁移项目（Python）
---

## Docker容器迁移流程总结

经过半年知识的积累，从了解go语言开始展开对docker源码的阅读，熟悉了docker的代码架构和命令执行流程，通过分析docker checkpoint命令执行流程的分析，进一步阅读containerd模块，containerd－shim
模块的代码,containerd模块负责对容器生命周期进行管理，containerd－shim则是用于封装接口对接runc模块的夹层代码，runc模块则用于封装lincontainerd来实现满足OCI标准的容器。而docker容器检查点创建的实现需要runc调用criu第三方工具，所以进一步我需要深入criu对进程进行检查点创建和恢复的过程，其中涉及到了很多C语言的基础知识以及Unix编程技巧。最后在掌握所有这些技术基础后，开始以phaul项目为基础来实现对docker容器热迁移的过程，phaul是一个利用criu第三方的工具来实现对进程热迁移流程的项目。python编写，所以目前我同样采取phaul编程架构然后利用docker checkpoint／start的技术支持来实现对docker容器进行热迁移的项目。


编程架构图：
![LiveMigrationFramework](/img/LiveMigrationFramework.png)


### 热迁移流程描述：
项目使用描述：

* 1.宿主机和目的机同时开启docker－migrator service服务：./docker-migrator-switch service
* 2.在宿主机端启动docker容器迁移服务：./docker-migrator-switch client ip ct_id(Ex:./docker-migrator-switch client 192.168.58.130 e42eqasdaaa221)

热迁移过程描述：

* 1.验证cpu信息：通过发送criureq的cpucheck请求验证cpu信息是否满足需求
* 2.验证criu版本是否匹配：源主机的criu版本必须低于目的机criu版本
* 3.文件系统迁移：
  迁移的文件目录包括：
  ![migration_fs](/img/fs_migration.png)
  
* 4.内存迭代迁移，目前还没有实现，暂时的实现思路是通过调用criu pre-dump来实现
* 5.Stop-And-Copy，达到阈值条件进行最后一轮备份及迭代传输
* 6.传输检查点镜像文件，目的端进行恢复，恢复成功后，发送响应，源端关闭容器