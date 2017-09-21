import threading
import logging
import traceback
import socket
import select



class rpc_server_daemon(threading.Thread):
    def __init__(self,rpc_migrate_service,connection):
        threading.Thread.__init__(self)
        self.srv_manager = _rpc_server_manager(rpc_migrate_service,connection)
        self._stop_fd = None
    
    def run(self):
        try:
            self.srv_manager.loop(self._stop_fd)
        except Exception:
            logging.exception("Exception in rpc_server_thread")
    
    def init_stop_fd(self):
        sks = socket.socketpair()
        self.stop_fd = sks[0]
        return sks[1]

class _rpc_server_manager(object):
    def __init__(self,rpc_service,connection):
        self._rpc_migrate_service = rpc_service
        self._connection = connection
        self._poll_list = []
        self._alive = True
        self.add_poll_item(_rpc_server_sk(connection.fdrpc))
        
    def add_poll_item(self, item):
		self._poll_list.append(item)

    def remove_poll_item(self, item):
		self._poll_list.remove(item)

    def make_master(self):
        return self._rpc_migrate_service(self._connection)

    def stop(self):
        self._alive=False

    def loop(self,stop_fd):
        if stop_fd :
            self.add_poll_item(_rpc_stop_fd(stop_fd))
        while self._alive:
            r, w, x = select.select(self._poll_list, [], [])
	    for sk in r:
		sk.work(self)
            
#wrap the stop_fd with the data process
class _rpc_stop_fd(object):
    def __init__(self,fd):
        self._fd = fd
    
    def fileno(self):
        return self._fd.fileno()

    def work(self,mgr):
        mgr.stop()

#wrap the sk with the data process
rpc_sk_buf = 16384
RPC_CMD = 1
RPC_CALL = 2

RPC_RESP = 1
RPC_EXC = 2
class _rpc_server_sk(object):
    def __init__(self,sk):
        self._sk = sk
        self._master = None
    
    def fileno(self):
        return self._sk.fileno()

    def work(self,server_manager):
        raw_data = self._sk.recv(rpc_sk_buf)
        if not raw_data:
            server_manager.remove_poll_item(self)
            if self._master:
                self._master.dis_connect()
                return
        rpc_list = eval(raw_data)
        try:
            if rpc_list[0] == RPC_CALL:
                if not self._master:
                    raise Exception("Service not setup yet!  init_rpc First!")
                res = getattr(self._master,"rpc_"+data[1])(*data[2])
            elif rpc_list[0] == RPC_CMD:
                res = getattr(self,data[1])(mgr,*data[2])
            else :
                raise Exception("Rpc type is not exist except CALL and CMD!")
        except Exception as e :
            traceback.print_exc()
            res = (RPC_EXC,e)
        else :
            res = (RPC_RESP,res)

            raw_resp = repr(res)
            self._sk.send(raw_resp)
    
    def init_rpc(self,mgr,args):
        #setup rpc service
        self._master = mgr.make_master()
        self._master.on_connect()
