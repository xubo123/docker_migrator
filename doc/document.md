## Docker_Migrator Document
***
### Introduction
***
This document describes how to setup the docker container live_migration environment.Except the docker_migrator project,we also do some modification in docker source code in order to support docker container's live_migration based on the 17.04 version.you can also clone the code of docker from my github repository.

### 1.Requirements
***
* Linux kernel 3.5(Ubuntu)
* Python 2.7
* Go 1.6.2
* Version Contro tools Repo and Git

### 2.Setup Environment
***

#### 2.1 Prepare migration node
For migration experiment,you have to prepare two host machine,one for source node and one for target node.You can implement the environment by start two Ubuntu virtual machine by vmware Workstation 12 Player.

#### 2.2 Setup Criu Tools

The setup procedure is given on the website <https://criu.org/Installation>,and the 3.1 version is recommended. 

#### 2.3 Compile Docker Source Code
There is a few changes in the Docker source code we use,so as to support the live_migration.You can get the code from my github by following cmd:
```
cd /$GOPATH
git clone -b docker_for_migration https://github.com/xubo123/docker.git 
```
Then you can follow the introduction :
##### Ubuntu:
1. setup docker binary:
```
# sudo apt-get install docker-ce
```
2. enter into the docker source code dir and compile:
```
# cd /$GOPATH
# make
```
3. copy the compiled docker binary to /usr/bin:
```
# cp ./bundle/17.04-dev/docker-daemon/docker* /usr/bin
# cp ./bundle/17.04-dev/docker-client/docker* /usr/bin
```

#### 2.4 Build consul cluster
What's consul? consul is a service management software.It support service register and discovery,k-v store ,and strong consistency protocol.Here we use consul to help us to set up overlay network.You can follow the introduction to setup consul.

1. Setup and configure consul
```
# wget https://releases.hashicorp.com/consul/0.8.1/consul_0.8.1_linux_amd64.zip?_ga=1.206478483.1894250111.1493627304
# unzip consul_0.8.1_linux_amd64.zip
# sudo cp consul /usr/local/bin/
```
2. Start server and client:
```
//on the source node,ip for ex:192.168.58.135
# sudo nohup consul agent -server -bootstrap  -data-dir /opt/consul -bind=192.168.58.135 -node-id=$(cat /proc/sys/kernel/random/uuid) &
//on the target node,ip for ex:192.168.58.130
# sudo nohup consul agent -data-dir /opt/consul  -bind=192.168.58.130  -node-id=$(cat /proc/sys/kernel/random/uuid) &
```
3. Connect the server and client:
```
// on the target node:
# consul join 192.168.58.135
```
4. Check whether success to connect:
```
// on the source and target node:
consul members
```

#### 2.5 Start docker
1. First all, you have make sure docker-ce is stopped:
```
service docker stop
```
2. Then start docker by the binary you have compiled:
```
//You have to make sure that the flag --cluster-advertise is corresponding to the ethernet card like ens33:2375 or eth0:2375
# sudo /usr/bin/dockerd --experimental -H tcp://0.0.0.0:2375 -H unix:///var/run/docker.sock \
--cluster-store=consul://localhost:8500 --cluster-advertise=ens33:2375 &
// If you want to start docker with overlay fs driver:
# sudo /usr/bin/dockerd --experimental -s overlay -H tcp://0.0.0.0:2375 -H unix:///var/run/docker.sock \
--cluster-store=consul://localhost:8500 --cluster-advertise=ens33:2375 &
```

#### 2.6 Construct OVERLAY Network

1. Create overlay network
```
# docker network create -d overlay multihost
```
2. Check
```
//you should see 'multihost' network by the cnd
# docker network ls
```
#### 2.7 Start Docker Container
For example:

```
//Dockerfile:
FROM redis
CMD ["/usr/local/bin/redis-server"]
```
1. Build docker redis-image:
```
# cd /DOCKERFILE_DIR
# docker build -t redis_image .
```
2. Run redis container
```
# docker run -di --name=reids --net=multihost redis_image
//you can see the redis container is runnig by cmd :
# docker ps
```

### 3 Live Migrate Docker Container
1. First,you should configure two nodes that can transfer file or directory by rsync without password:<http://www.jb51.net/article/60192.htm>
2. Start docker_migrator service daemon:
```
// you should execute following cmd with root permission
# cd /docker_migrator
# ./docker_migrator_switch.py service
```
3. Start migrate redis container
```
# cd /docker_migrator
//target node ip :192.168.58.130
#./docker_migrator_switch client --keep-images --pre-dump --fs-driver aufs 192.168.58.130 $redis_container_id 
```
4.You can see the migration result by log output,and if the container restore failed in the target,it also start again in the source node.

### 4 Contact Me
If you have any question in the setup procedure ,you can tell us and contact us by the Email:

* 786748095@qq.com


