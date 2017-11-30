import logging
import os 
import shutil
import tarfile
import tempfile
import threading
import time
import tool.util
import tool.criu_api
import subprocess as sp
def_path = "/var/local/docker_migrator_ck"

class opendir(object):
    def __init__(self, path):
        self._dirname = path
        self._dirfd = os.open(path, os.O_DIRECTORY)
        tool.util.set_cloexec(self)

    def close(self):
        os.close(self._dirfd)
        os._dirname = None
        os._dirfd = -1

    def name(self):
        return self._dirname

    def fileno(self):
        return self._dirfd

class untar_thread(threading.Thread):
    def __init__(self, sk, tdir):
        threading.Thread.__init__(self)
        self.__sk = sk
        self.__dir = tdir

    def run(self):
        try:
            tf_fileobj = tool.util.tarfile_fileobj_wrap(self.__sk)
            tf = tarfile.open(mode="r|", fileobj=tf_fileobj)
            tf.extractall(self.__dir)
            tf.close()
            tf_fileobj.discard_unread_input()
        except Exception:
            logging.exception("Exception in untar_thread")

class img_tar(object):
    def __init__(self, sk, dirname):
        tf_fileobj = tool.util.tarfile_fileobj_wrap(sk)
        self.__tf = tarfile.open(mode="w|", fileobj=tf_fileobj)
        self.__dir = dirname

    def add(self, img, path=None):
        if not path:
            path = os.path.join(self.__dir, img)

        self.__tf.add(path, img)

    def close(self):
        self.__tf.close()

class lm_docker_img(object):
    WDIR = 1
    IMGDIR = 2
    def __init__(self, typ):
        self.current_iter = 0
        self.sync_time = 0.0
        self.sync_time_list = []
        self._keep_on_close = False
        self._work_dir = None
        self._current_dir = None
        self._criu_work_dir = None
        self._type = typ

    def set_options(self, opts):

        self._keep_on_close = opts["keep_images"]
        suf = time.strftime("-%y.%m.%d-%H.%M", time.localtime())
        tool.util.makedirs(opts["img_path"])
        wdir = tempfile.mkdtemp(suf, "%s-" % self._type, opts["img_path"])
        self._work_dir = opendir(wdir)
        self._img_path = os.path.join(self._work_dir.name(), "img")
        os.mkdir(self._img_path)

    def sync_imgs_to_target(self, dest_rpc_caller, migrate_worker, sk, thost,pre_dump):
		# Pre-dump doesn't generate any images (yet?)
		# so copy only those from the top dir
        logging.info("Sending images to target")
        start = time.time()
        cdir = self.image_dir()
        ck_dir = os.path.join(cdir, migrate_worker.get_ck_dir())
        dest_rpc_caller.start_accept_images(lm_docker_img.IMGDIR)
        tf = img_tar(sk, ck_dir)

        logging.info("\tPack")
        logging.info("ck_dir:===== %s", ck_dir)
        for img in filter(lambda x: x.endswith(".img"), os.listdir(ck_dir)):
            logging.info("the image to be transffered :%s",img)
            tf.add(img)
        logging.info("\tAdd migrate_worker images")
        self._criu_work_dir = ck_dir+"/criu.work"
        if self.current_iter <= 1:
            if pre_dump:
                himg = migrate_worker.get_meta_images(ck_dir, pre_dump, self.current_iter)
                logging.info("meta images:%s,%s", himg[1], himg[0])
                tf.add(himg[1], himg[0])
            else:
                for himg in migrate_worker.get_meta_images(ck_dir, pre_dump, self.current_iter):
                    logging.info("meta images:%s,%s", himg[1], himg[0])
                    tf.add(himg[1], himg[0])
        else:
            for himg in migrate_worker.get_meta_images(ck_dir, pre_dump, self.current_iter):
                logging.info("meta images:%s,%s", himg[1], himg[0])
                tf.add(himg[1], himg[0])
        tf.close()

        target_imagepath = dest_rpc_caller.get_image_dir()
        dst = "%s:%s" % (thost, os.path.join(target_imagepath, migrate_worker.get_ck_dir()))
        sp.call(["rsync", "-a", self._criu_work_dir, dst])
        logging.info("Command: rsync -a %s %s", self._criu_work_dir, dst)
        dest_rpc_caller.stop_accept_images()

        self.sync_time = time.time() - start
        self.sync_time_list.append(self.sync_time)

    def save_images(self):
        logging.info("Keeping images")
        self._keep_on_close = True

    def image_dir(self):
        return self._current_dir.name()

    def close(self):
        if not self._work_dir:
            return

        self._work_dir.close()
        if self._current_dir:
            self._current_dir.close()

        if not self._keep_on_close:
            logging.info("Removing images")
            shutil.rmtree(self._work_dir.name())
        else:
            logging.info("Images are kept in %s", self._work_dir.name())
        pass

    def criu_work_dir(self):
        return self._criu_work_dir
    def work_dir(self):
        return self._work_dir.name()

    def work_dir_fd(self):
        return self._work_dir.fileno()

    def image_dir_fd(self):
        return self._current_dir.fileno()

    def parent_image_dir(self,ck_name):
        img_dir = os.path.join("%s/%d" % (self._img_path, self.current_iter-1),ck_name)
        logging.info("\tParent directory %s", img_dir)
        parent_dir = opendir(img_dir)
        return parent_dir.name()

    def new_image_dir(self):
        if self._current_dir:
            self._current_dir.close()
        self.current_iter += 1
        img_dir = "%s/%d" % (self._img_path, self.current_iter)
        logging.info("\tMaking directory %s", img_dir)
        os.mkdir(img_dir)
        self._current_dir = opendir(img_dir)

    def send_cpuinfo(self, dest_rpc_caller, sk):
        dest_rpc_caller.start_accept_images(lm_docker_img.WDIR)
        tf = img_tar(sk, self.work_dir())
        tf.add(tool.criu_api.cpuinfo_img_name)
        tf.close()
        dest_rpc_caller.stop_accept_images()

    def start_accept_images(self, dir_id, migrate_worker, sk):
        if dir_id == lm_docker_img.WDIR:
            dirname = self.work_dir()
        else:
            dirname = self.image_dir()
            dirname = os.path.join(dirname, migrate_worker.get_ck_dir())
        self._criu_work_dir = dirname+"/criu.work"
        self.__acc_tar = untar_thread(sk, dirname)
        self.__acc_tar.start()
        logging.info("Started images server")

    def stop_accept_images(self):
        logging.info("Waiting for images to unpack")
        self.__acc_tar.join()

    def img_sync_time(self):
        return self.sync_time

    def img_sync_time_list(self):
        return self.sync_time_list
