import json
import logging
import os
import signal
import subprocess as sp
from subprocess import PIPE
import time
import client.fs_migrator

docker_bin = "/usr/bin/docker"
docker_dir = "/var/lib/docker/"
docker_run_state_dir = "/var/run/runc/"
docker_run_meta_dir = "/run/runc/"
AUFS = "aufs"
OVERLAY = "overlay"

class docker_lm_worker(object):
    def __init__(self,ct_id):
        if len(ct_id) < 3:
            raise Exception("Container id must > 3 digits!")
        self._ct_id = ct_id
        self._ct_rootfd = ""
        
    def set_options(self,opts):
        pass

    def init_src(self,fs_driver):

        self.full_ctid = self.get_full_ctid()
        self._mnt_id = self.get_mount_id(fs_driver)
        self.diff_ids = self.get_diff_id(fs_driver)
        if fs_driver == AUFS:
            self._mnt_diff_ids = self.get_mnt_diff_ids()
        elif fs_driver == OVERLAY :
            self._lower_dir_id = self.get_lower_dir_id()
        self._volumes_names = self.get_volumes_name()
        self.image_id = self.get_image_id()
        self.load_fs_dir(fs_driver)

        self.load_ct_config(docker_dir)
    def init_dst(self):
        pass     

    def get_full_ctid(self):
        container_dirlist = os.listdir(os.path.join(docker_dir,"containers"))
        full_id = ""
        for container_dir in container_dirlist:
            container_dir = container_dir.rsplit("/")
            if (container_dir[0].find(self._ct_id)==0):
                full_id = container_dir[0]
                break
        if full_id!="":
            return full_id
        else :
            raise Exception("Cannot find container full_id!")
    
    def umount(self):
		pass
    
    def root_task_pid(self):
		return self.full_ctid
    def load_fs_dir(self,fs_driver):
        if(fs_driver == AUFS):
            self.load_aufs_dir()
        elif fs_driver == OVERLAY:
            self.load_overlay_dir()

    def load_aufs_dir(self):
        #/var/lib/docker/aufs/mnt/mnt_id
        self._ct_rootfs = os.path.join(
                        docker_dir, "aufs/mnt", self._mnt_id)
        self._topdiff_dir = os .path.join(docker_dir,"aufs/diff",self._mnt_id)
        self._ct_init_rootfs = os.path.join(
                        docker_dir, "aufs/mnt", self._mnt_id+"-init")
        #/var/lib/docker/image/aufs
        self.load_image_dir(AUFS)
        #/var/lib/docker/aufs/diff
        self._mnt_diff_dirs = []
        for mnt_diff_id in self._mnt_diff_ids:
              mnt_diff_dir = os.path.join(docker_dir,"aufs/diff",mnt_diff_id)
              self._mnt_diff_dirs.append(mnt_diff_dir)
        #/var/lib/docker/aufs/layers
        self._ct_layers_dirs = [os.path.join(docker_dir,"aufs/layers",self._mnt_id+"-init")]
        for mnt_layers_id in self._mnt_diff_ids:
              mnt_layers_dir = os.path.join(docker_dir,"aufs/layers",mnt_layers_id)
              self._ct_layers_dirs.append(mnt_layers_dir)
        #/var/lib/docker/volumes
        self.load_volume_dir()
        logging.info("Container rootfs: %s", self._ct_rootfs)
        logging.info("Container mounts_dir: %s", self._ct_layerdb_dir)
        logging.info("Container layers : %s",self._ct_layers_dirs)
        logging.info("Container diff : %s",self._ct_diff_dirs)
        logging.info("Container volumes : %s",self._ct_volumes_dirs)

    def load_overlay_dir(self):
        #/var/lib/docker/overlay/mnt_id
        self._ct_rootfs = os.path.join(
                        docker_dir, "overlay", self._mnt_id)
        self._upper_dir = os.path.join(self._ct_rootfs,"upper")
        self._work_dir = os.path.join(self._ct_rootfs,"work")
        self._lower_id = os.path.join(self._ct_rootfs,"lower-id")
        self._ct_init_rootfs = os.path.join(
                        docker_dir, "overlay", self._mnt_id+"-init")  
        #/var/lib/docker/image/overlay
        self.load_image_dir(OVERLAY)
        #/var/lib/docker/overlay/lower_id
        self._ct_lower_dir = os.path.join(
                        docker_dir, "overlay", self._lower_dir_id)
        #/var/lib/docker/volumes
        self.load_volume_dir()                
        logging.info("Container rootfs: %s", self._ct_rootfs)
        logging.info("Container lower_dir : %s",self._ct_lower_dir)
        logging.info("Container mounts_dir: %s", self._ct_layerdb_dir)
        logging.info("Container diff : %s",self._ct_diff_dirs)
        logging.info("Container volumes : %s",self._ct_volumes_dirs)
        
    def load_image_dir(self,fs_driver):
        #layers relationship /var/lib/docker/image/fsdriver/layerdb/mounts  
        self._ct_layerdb_dir = os.path.join(docker_dir,"image/"+fs_driver+"/layerdb/mounts/"+self.full_ctid)
        #layers relationship /var/lib/docker/image/fsdriver/layerdb/sha256 
        self._ct_diff_dirs = []
        for diff_id in self.diff_ids :
             _ct_diff_dir = os.path.join(docker_dir,"image/"+fs_driver+"/layerdb/sha256/"+diff_id)
             self._ct_diff_dirs.append(_ct_diff_dir)
        #/var/lib/docker/image/fsdriver/imagedb/content/sha256(/metadata/sha256)
        self._ct_image_dir = os.path.join(docker_dir,"image/"+fs_driver+"/imagedb/content/sha256/"+self.image_id)
        self._ct_imagemeta_dir = os.path.join(docker_dir,"image/"+fs_driver+"/imagedb/metadata/sha256/"+self.image_id)
        
    def load_volume_dir(self):
        #/var/lib/docker/volumes
        self._ct_volumes_dirs = []
        if self._volumes_names!=None : 
            if  self._volumes_names[0] == 1:
                for volumes_name in self._volumes_names[1:] :
                    volumes_dir = os.path.join(docker_dir,"volumes",volumes_name)
                    self._ct_volumes_dirs.append(volumes_dir)
            elif self._volumes_names[0] == 2 :
               for volumes_name in self._volumes_names[1:] :
                    self._ct_volumes_dirs.append(volumes_name)
    def load_ct_config(self,path):
        #config.v2.json
        self._ct_config_dir = os.path.join(
                        docker_dir, "containers", self.full_ctid)
        #/run/runc
        self._ct_run_meta_dir = os.path.join(
                        docker_run_meta_dir, self.full_ctid)
        self._ct_run_state_dir = os.path.join(
			docker_run_state_dir, self.full_ctid)
        logging.info("Container config: %s", self._ct_config_dir)
        logging.info("Container meta: %s", self._ct_run_meta_dir)
        logging.info("Container state: %s", self._ct_run_state_dir)

    def get_fs(self,fs_driver,fdfs=None):
        # use rsync for rootfs and configuration directories
        lm_fs_dir = [self._ct_config_dir,self._ct_layerdb_dir,self._ct_image_dir]
        if fs_driver == AUFS:
            lm_fs_dir.extend(self._ct_layers_dirs)
            lm_fs_dir.extend(self._mnt_diff_dirs)
        elif fs_driver == OVERLAY:
            lm_fs_dir.append(self._ct_lower_dir)
            lm_fs_dir.append(self._upper_dir)
            lm_fs_dir.append(self._work_dir)
            lm_fs_dir.append(self._lower_id)
            lm_fs_dir.append(self._ct_init_rootfs)
        lm_fs_dir.extend(self._ct_diff_dirs)
        lm_fs_dir.extend(self._ct_volumes_dirs)
        if os.path.exists(self._ct_imagemeta_dir):
           lm_fs_dir.append(self._ct_imagemeta_dir)
        return client.fs_migrator.lm_docker_fs(lm_fs_dir)

    def get_mount_id(self,fs_driver):
        container_id = self.full_ctid
        mount_path = os.path.join("/var/lib/docker/image/",fs_driver+"/layerdb/mounts/"+container_id+"/mount-id")
        logging.info("mount_path:%s",mount_path)
        try:
            fd = open(mount_path)
            mnt_id = fd.read()
        finally:
            fd.close()

        logging.info("mnt_id:%s",mnt_id)
        return mnt_id

    

    def get_diff_id(self,fs_driver):
        parent_diff_id = self.full_ctid
        mounts_root =  os.path.join(docker_dir,"image/"+fs_driver+"/layerdb/mounts")
        diff_id_root =  os.path.join(docker_dir,"image/"+fs_driver+"/layerdb/sha256")
        parent_path = os.path.join(mounts_root,parent_diff_id+"/parent")
        logging.info("parent_path:%s",parent_path)
        diff_ids = []
        while os.path.exists(parent_path) :
            logging.info("parent_path:%s",parent_path)
            parent_file = open(parent_path)
            try:
                diff_id = parent_file.read()
                diff_id = diff_id[7:]
                diff_ids.append(diff_id)
            finally:
                parent_file.close()
            parent_path = os.path.join(diff_id_root,diff_id+"/parent")
            logging.info("end_parent_path:%s",parent_path)
        return diff_ids

    def get_volumes_name(self):
        config_path = os.path.join(docker_dir,"containers",self.full_ctid,"config.v2.json")
        config_file = open(config_path)
        volumes_names = [0]
        external_volumes = [0]
        try:
            config_json_str = config_file.read()
            config_json = json.loads(config_json_str)
            mount_point = config_json['MountPoints']
            logging.info("mount_point:%s",mount_point)
            for key,value in mount_point.items():
                logging.info("key,value:%s,%s",key,value)
                if value["Name"]!="":
                   volumes_names[0] = 1
                   volumes_names.append(value["Name"])
                   logging.info("default volumes_name:%s",value["Name"])
                   break
                elif value["Source"]!="":
                   external_volumes[0] = 2
                   external_volumes.append(value["Source"])
                   logging.info("external volumes_name:%s",value["Source"])
        finally:
            config_file.close()
        if volumes_names[0]:
           return volumes_names
        elif external_volumes[0]:
           return external_volumes
        else:
           return None
    
    def get_image_id(self):
        config_path = os.path.join(docker_dir,"containers",self.full_ctid,"config.v2.json")
        config_file = open(config_path)
        image_id = ""
        try:
            config_json_str = config_file.read()
            config_json = json.loads(config_json_str)
            image_id = config_json["Image"]
        finally:
            config_file.close()
        return image_id[7:]
    

    def get_mnt_diff_ids(self):
        parent_ids_path = os.path.join(docker_dir,"aufs/layers",self._mnt_id)
        parent_ids = []
        parent_ids.append(self._mnt_id)
        try:
            parent_ids_file = open(parent_ids_path)
            while 1:
                parent_id= parent_ids_file.readline()
                if not parent_id:
                    break
                parent_id = parent_id.strip()
                logging.info("parent_id:%s",parent_id)
                parent_ids.append(parent_id)
        finally:
            parent_ids_file.close()
        return parent_ids

    def get_lower_dir_id(self):
        lower_id_path = docker_dir+"overlay/"+self._mnt_id+"/lower-id"
        logging.info("overlay lower_id_path:%s",lower_id_path)
        lower_id = ""
        try :
            lower_id_file = open(lower_id_path)
            lower_id = lower_id_file.readline()
            lower_id = lower_id.strip()
            logging.info("overlay lower_id:%s",lower_id)
        finally :
            lower_id_file.close()
        return lower_id

    def get_meta_images(self, path,pre_dump_flag,iterCount):
	# Send the meta state file with criu images
        state_path = os.path.join(self._ct_run_state_dir, "state.json")
        desc_path = os.path.join(path, "descriptors.json")
        config_path = os.path.join(path,"config.json")
        if iterCount <=1:
           if pre_dump_flag:
              logging.info("pre_dump config_path:%s",config_path)
              return (config_path,"config.json")
           else:
              return (desc_path, "descriptors.json"),(config_path,"config.json")
        else:
            parent_path = os.path.join(path,"parent")
            if pre_dump_flag:
              logging.info("pre_dump config_path:%s",config_path)
              return (config_path,"config.json"),(parent_path,"parent")
            else:
              return (desc_path, "descriptors.json"),(config_path,"config.json"),(parent_path,"parent")


    def put_meta_images(self, dir,ctid,ck_dir):
        # Create docker runtime meta dir on dst side
        logging.info("ctid=====%s",self._ct_id)
        self.full_ctid = self.get_full_ctid()
      	self.load_ct_config(docker_dir)    


    def pre_dump(self,pid,img,fs):
        logging.info("Pre-Dump container %s",pid)

        log_fd = open("/tmp/docker_pre_checkpoint.log","w+")
        image_path_opt = "--checkpoint-dir="+ img.image_dir()
        if img.current_iter <= 1:
            logging.info("No parentpath pre-dump:%d",img.current_iter)
            ret = sp.call([docker_bin, "checkpoint","create","--pre-dump", image_path_opt, self._ct_id,self.get_ck_dir()],
                                        stdout=log_fd, stderr=log_fd)
        else:
            logging.info("Pre-Dump with Parentpath")
            parent_path = "--parent-path=../../%d/%s" % (img.current_iter-1,self.get_ck_dir())
            ret = sp.call([docker_bin, "checkpoint","create","--pre-dump", image_path_opt, parent_path, self._ct_id,self.get_ck_dir()],
                                        stdout=log_fd, stderr=log_fd)
        if ret != 0:
            raise Exception("docker pre_checkpoint failed") 

    def final_dump(self,pid,img,fs):
        logging.info("Last dump container %s",pid)

        log_fd = open("/tmp/docker_checkpoint.log","w+")
        image_path_opt = "--checkpoint-dir="+ img.image_dir()
        ret = 1
        if img.current_iter <= 1:
           logging.info("No parentpath dump:%d",img.current_iter)
           ret = sp.call([docker_bin, "checkpoint","create", image_path_opt, self._ct_id,self.get_ck_dir()],
                                        stdout=log_fd, stderr=log_fd)
        else :
           logging.info("Dump with Parentpath")
           #parent_path = "--parent-path="+img.parent_image_dir(self.get_ck_dir()) 
           parent_path = "--parent-path=../../%d/%s" % (img.current_iter-1,self.get_ck_dir())
           ret = sp.call([docker_bin, "checkpoint","create", image_path_opt, parent_path, self._ct_id,self.get_ck_dir()],
                                        stdout=log_fd, stderr=log_fd)
        if ret != 0:
			raise Exception("docker checkpoint failed")

    
    def final_restore(self, img, criu,ck_dir):
        log_fd = open("/tmp/docker_restore.log", "w+")
        image_path_opt = "--checkpoint-dir=" + img.image_dir()
        logging.info("restore command:%s",[docker_bin, "start", image_path_opt,"--checkpoint="+ck_dir, self._ct_id])
        ret = sp.call([docker_bin, "start", image_path_opt,"--checkpoint="+self.get_ck_dir(), self._ct_id],
					stdout=log_fd, stderr=log_fd)
        if ret != 0:
             logging.info("docker restore failed")
        return ret
    

    def get_ck_dir(self):
        return  self._ct_id+"_checkpoint"
    
    def migration_complete(self, fs, target_host):
	pass

    def migration_fail(self, fs):
	pass
