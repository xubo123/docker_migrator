import errno
import logging
import client.rpc_client
import client.docker_migrate_worker
import tool.criu_api
import tool.criu_req

MIGRATION_MODE_LIVE = "live"
MIGRATION_MODE_RESTART = "restart"
MIGRATION_MODES = (MIGRATION_MODE_LIVE, MIGRATION_MODE_RESTART)

class migration_iter_controller(object):
    def __init__(self,ct_id,dst_id,connection,mode):
        self._mode = mode
        self.connection = connection
        self.dest_rpc_caller = client.rpc_client._rpc_client(self.connection.fdrpc)

        logging.info("Locally setting up!")
        self._migrate_worker =client.docker_migrate_worker.docker_lm_worker(ct_id)
        self._migrate_worker.init_src()
        self.fs = self._migrate_worker.get_fs(self.connection.fdfs)
        if not self.fs:
            raise Exception("No fs driver found!")
        self.img = client.img_migrator.lm_docker_img("dump")
        self.criu_connection = criu_api.criu_conn(self.connection.mem_sk)
        logging.info("Remote Setting up!")
        ct_id = dst_id if dst_id else ct_id
        self.dest_rpc_caller.setup(ct_id,mode)
    
    def set_options(self,opts):
        self.__force = opts["force"]
        self.__skip_cpu_check = opts["skip_cpu_check"]
        self.__skip_criu_check = opts["skip_criu_check"]
        self._migrate_worker.set_options(opts)
	self.fs.set_options(opts)
	if self.img:
		self.img.set_options(opts)
	if self.criu_connection:
		self.criu_connection.set_options(opts)
        self.dest_rpc_caller.set_options(opts)
    
    def start_live_migration(self):
        self.fs.set_work_dir(self.img.work_dir())
        self.__validate_cpu()
        self.__validate_criu_version
        root_pid = self._migrate_worker.root_task_pid()
        migration_stats = mstats.live_stats()
	migration_stats.handle_start()

        # Step1 : FS migration
        logging.info("FS migration start!")
        fsstats = self.fs.start_migration()
	migration_stats.handle_preliminary(fsstats)
        
        #Step2 : pre-dump TODO

        #Step3 : Stop and Copy ,Final dump and restore!
        logging.info("Final dump and restore! ")
        self.dest_rpc_caller.start_iter(False)
        self.img.new_image_dir()
        self._migrate_worker.final_dump(root_pid,self.img,self.criu_connection,self.fs)
        self.dest_rpc_caller.end_iter()
        
        #Step4 :Restore and CLean!
        try:
			# Handle final FS and images sync on frozen htype
		logging.info("Final FS and images sync")
		fsstats = self.fs.stop_migration()
		self.img.sync_imgs_to_target(self.target_host, self.htype,
										self.connection.mem_sk)

			# Restore htype on target
		logging.info("Asking target host to restore")
		self.dest_rpc_caller.restore_from_images(self._migrate_worker._ctid,self._migrate_worker.get_ck_dir())

	except Exception:
		self._migrate_worker.migration_fail(self.fs)
		raise

		# Restored on target, can't fail starting from this point
	try:
			# Ack previous dump request to terminate all frozen tasks
		resp = self.criu_connection.ack_notify()
		if not resp.success:
		    logging.warning("Bad notification from target host")

		dstats = criu_api.criu_get_dstats(self.img)
		migration_stats.handle_iteration(dstats, fsstats)

		logging.info("Migration succeeded")
		self._migrate_worker.migration_complete(self.fs, self.target_host)
		migration_stats.handle_stop(self)
		self.img.close()
		self.criu_connection.close()

	except Exception as e:
		logging.warning("Exception during final cleanup: %s", e)


    def __validate_cpu(self):
		if self.__skip_cpu_check or self.__force:
			return
		logging.info("Checking CPU compatibility")

		logging.info("\t`- Dumping CPU info")
		req = criu_req.make_cpuinfo_dump_req(self.img)
		resp = self.criu_connection.send_req(req)
		if resp.HasField('cr_errno') and (resp.cr_errno == errno.ENOTSUP):
			logging.info("\t`- Dumping CPU info not supported")
			self.__force = True
			return
		if not resp.success:
			raise Exception("Can't dump cpuinfo")

		logging.info("\t`- Sending CPU info")
		self.img.send_cpuinfo(self.dest_rpc_caller, self.connection.fdmem)

		logging.info("\t`- Checking CPU info")
		if not self.dest_rpc_caller.check_cpuinfo():
			raise Exception("CPUs mismatch")

    def __validate_criu_version(self):
		if self.__skip_criu_check or self.__force:
			return
		logging.info("Checking criu version")
		version = criu_api.get_criu_version()
		if not version:
			raise Exception("Can't get criu version")
		if not self.dest_rpc_caller.check_criu_version(version):
			raise Exception("Incompatible criu versions")
