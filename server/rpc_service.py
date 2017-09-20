#
#Help to operate on target host
#
import logging

class rpc_migrate_service(object):
    def __init__(self,connection):
        self.connection = connection
        self.docker_lm_worker = None
        self.criu_connection = None
        self.img = None
        self.__mode = iters.MIGRATION_MODE_LIVE
    
    def on_connect(self):
        logging.info("Rpc Service Connected!")
    
    def dis_connect(self):
        logging.info("Rpc Service Disconnected!")
        if self.criu_connection:
			     self.criu_connection.close()
        if self.docker_lm_worker:
		if iters.is_live_mode(self.__mode):
			self.docker_lm_worker.umount()
        if self.img:
	        logging.info("Closing images")
		if not self.restored:
			self.img.save_images()
		self.img.close()

    def rpc_setup(self,ct_id,mode):
        self.mode = mode
        self._migrate_worker = docker_lm_worker(ct_id)
        self._migrate_worker.init_src()
    
    def rpc_set_options(self,opts):
        self._migrate_worker.set_options(opts)
        if self.criu_connection:
	    self.criu_connection.set_options(opts)

        if self.img:
	    self.img.set_options(opts)
    
    def rpc_start_accept_images(self, dir_id):
         self.img.start_accept_images(dir_id, self.connection.fdmem)

    def rpc_stop_accept_images(self):
         self.img.stop_accept_images()
    
    def rpc_check_cpuinfo(self):
        logging.info("Checking cpuinfo")
        req = criu_req.make_cpuinfo_check_req(self.img)
        resp = self.criu_connection.send_req(req)
	logging.info("\t`- %s", resp.success)
	return resp.success

    def rpc_check_criu_version(self, source_version):
	logging.info("Checking criu version")
	target_version = criu_api.get_criu_version()
        if not target_version:
		logging.info("\t`- Can't get criu version")
		return False
	lsource_version = distutils.version.LooseVersion(source_version)
	ltarget_version = distutils.version.LooseVersion(target_version)
	result = lsource_version <= ltarget_version
	logging.info("\t`- %s -> %s", source_version, target_version)
	logging.info("\t`- %s", result)
	return result
    
    def rpc_start_iter(self, need_page_server):
	self.dump_iter_index += 1
        self.img.new_image_dir()
	if need_page_server:
		self.start_page_server()

    def rpc_end_iter(self):
        pass
    
    def rpc_restore_from_images(self,ctid,ck_dir):
	logging.info("Restoring from images")
	self._migrate_worker.put_meta_images(self.img.image_dir(),ctid,ck_dir)
	self._migrate_worker.final_restore(self.img, self.criu_connection,ck_dir)
	logging.info("Restore succeeded")
	self.restored = True
