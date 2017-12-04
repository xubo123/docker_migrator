## 1.docker_migrator
***
The docker_migrator tool is uesd for docker container live_migration.Docker container can move to target host from source with the help of docker_migrator,and there is no need to shutdown the container.

We introduce three important concept here to help us understand docker container's live_migration.

### 1.1 Live Migration

What's live migration,it's a very common kind of technique for vitual machine.In traditional Cloud_Platform enviroment,we have to schedule some virtual machine considering on load-balance,system upgrating or single-node-failure,and so on.But some special virtual machine which is running process like online-game,hpc aplication which can't undertake long-time breakdown.As a result,we should implement the technique that can migrate virtual machine with real-time status from node to node.

It's the same with docker container.With the development of docker container and more and more cloud_platform developer start to use docker container to deploy application,the technique of docker container's live_migration is especially important for container schedule.

### 1.2 Pre-Copy

Pre-Copy is a famous live-migration strategy ,docker_migrator adopt the pre-copy strategy to implement docker container live_migration.I'll give a brief description of live_migration(pre-copy) procedure.

* 1 FileSystem Migration:docker_migrator support two main kind of fs driver migration:AUFS,OVERLAY。
* 2 Memory iteration migration
* 3 Stop-and-Copy: The iteration will stop when the memory image file is small enough to make the migration transparent to application,or the iteration times reach the max times that we set before.
* 4 Restore: After the filesystem migration and memory iteration ,we will restore the docker container on the target.If we fail to restore the container,the container will restore on the source again.

### 1.3 CRIU
CRIU is a tool of process live_migration in user namespce.It can save checkpoint of process real-time status,and restore the process based on the checkpoint file.Docker_migrator is implemented with the help of criu tool.Detailed imformation:  <https://criu.org/Main_Page>  

## 2 How to use
***
We provide a detailed description of the [document](/doc/document.md) for you.The document tell you how to setup the experiment enviroment,and use docker_migrator to live_migrate docker container.

## 3 Licensing
***
Docker_migrator is licensed under the Apache License, Version 2.0. See [LICENSE](/LICENSE) for the full license text.

