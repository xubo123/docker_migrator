#
#Help to operate on target host
#
import logging

class rpc_migrate_service(object):
    def __init__(self,connection):
        self.connection = connection
    
    def on_connect(self):
        logging.info("Rpc Service Connected!")
    
    def dis_connect(self):
        logging.info("Rpc Service Disconnected!")