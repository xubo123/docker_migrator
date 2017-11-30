import logging
import os
import json
import subprocess as sp

rsync_log_file = "rsync.log"


class lm_docker_fs(object):
    def __init__(self, subtree_paths):
        self.__roots = []
        for path in subtree_paths:
            logging.info("Initialized subtree FS hauler (%s)", path)
            self.__roots.append(path)

        self.__thost = None

    def set_options(self, opts):
        self.__thost = opts["to"]

    def set_work_dir(self, wdir):
        self.__wdir = wdir

    def __run_rsync(self):
        logf = open(os.path.join(self.__wdir, rsync_log_file), "w+")

        for dir_name in self.__roots:

            dst = "%s:%s" % (self.__thost, os.path.dirname(dir_name))

			# First rsync might be very long. Wait for it not
			# to produce big pause between the 1st pre-dump and
			# .stop_migration

            ret = sp.call(
                ["rsync", "-a", dir_name, dst],
                stdout=logf, stderr=logf)
            logging.info("rsync -a "+dir_name+" "+dst+" result ret :%d",ret)
            if ret != 0 and ret != 24:
                raise Exception("Rsync failed")
    def __run_mnt_rsync(self,worker):
        logf = open(os.path.join(self.__wdir, rsync_log_file), "w+")
        #mnt_dir = worker._ct_rootfs
        top_diff_dir = worker._topdiff_dir
        rsync_flag = True
        while rsync_flag:

            #mnt_dst = "%s:%s" % (self.__thost, os.path.dirname(mnt_dir))
            topdiff_dst = "%s:%s" % (self.__thost, os.path.dirname(top_diff_dir))

			# First rsync might be very long. Wait for it not
			# to produce big pause between the 1st pre-dump and
			# .stop_migration
            #ret = sp.call(
            #    ["rsync", "-a", mnt_dir, mnt_dst],
            #    stdout=logf, stderr=logf)
            #logging.info("rsync -a "+mnt_dir+" "+mnt_dst+" result ret :%d", ret)
            ret = sp.call(
                ["rsync", "-a", top_diff_dir, topdiff_dst],
                stdout=logf, stderr=logf)
            logging.info("rsync -a "+top_diff_dir+" "+topdiff_dst+" result ret :%d", ret)
            
            if ret == 0:
                rsync_flag = False
            if ret != 0 and ret != 24:
                raise Exception("Rsync failed")

    def __run_upper_dir_sync(self,worker):
        logf = open(os.path.join(self.__wdir, rsync_log_file), "w+")
        upper_dir = worker._upper_dir
        rsync_flag = True
        while rsync_flag:

            upper_dst = "%s:%s" % (self.__thost, os.path.dirname(upper_dir))

			# First rsync might be very long. Wait for it not
			# to produce big pause between the 1st pre-dump and
			# .stop_migration
            ret = sp.call(
                ["rsync", "-a", upper_dir, upper_dst],
                stdout=logf, stderr=logf)
            logging.info("rsync -a "+upper_dir+" "+upper_dst+" result ret :%d", ret)
            
            if ret == 0:
                rsync_flag = False
            if ret != 0 and ret != 24:
                raise Exception("Rsync failed")

    def __run_last_rsync(self,worker):
        logf = open(os.path.join(self.__wdir, rsync_log_file), "w+")
        dir_name = worker._ct_config_dir
        dump_done = False
        # Wait for dump process done!
        while not dump_done:
            config_file = open(os.path.join(dir_name,"config.v2.json"))
            try:
                config_json_str = config_file.read()
                config_json = json.loads(config_json_str)
                run_state = config_json['State']['Running']
                logging.info("Running State:"+repr(run_state))
                if not run_state:
                    dump_done = True
            finally:
                config_file.close()
        # Start last rsync process
        rsync_flag = True
        while rsync_flag:

            dst = "%s:%s" % (self.__thost, os.path.dirname(dir_name))
            ret = sp.call(
                ["rsync", "-a", dir_name, dst],
                stdout=logf, stderr=logf)
            logging.info("rsync -a "+dir_name+" "+dst+" result ret :%d", ret)
            if ret == 0:
                rsync_flag = False
            if ret != 0 and ret != 24:
                raise Exception("Rsync failed")
    def start_migration(self,fs_driver,caller,worker):
        logging.info("Starting FS migration")
        self.__run_rsync()
        if fs_driver == "overlay":
            caller.mk_merged_dir(worker._ct_rootfs)
        return None

    def next_iteration(self):
        return None

    def stop_migration(self,worker):
        logging.info("Doing final container config sync")
        self.__run_last_rsync(worker)
        return None
    def mnt_diff_sync(self,worker):
        logging.info("Doing mnt and top diff sync")
        self.__run_mnt_rsync(worker)
        return None
    def upper_dir_sync(self,worker):
        logging.info("Doing upper_dir sync")
        self.__run_upper_dir_sync(worker)
        return None
    def rwlayer_sync(self,worker,fs_driver):
        if fs_driver == "aufs":
            self.mnt_diff_sync(worker)
        elif fs_driver == "overlay":
            self.upper_dir_sync(worker)
	# When rsync-ing FS inodes number will change
    def persistent_inodes(self):
        return False
