import logging
import socket
import tool.util

class connection(object):
    """docker migrate service connection
    the Class include all socket fd info about data transmit
    """

    def __init__(self,fdmem,fdrpc,fdfs):
        self.fdmem = fdmem
        self.fdrpc = fdrpc
        self.fdfs = fdfs

    def close(self):
        self.fdmem.close()
        self.fdrpc.close()


def establish(fdmem,fdrpc,fdfs):
    """ Build socket from fd,And return the connection class wrapping the socket
        We build the socket with the type of SOCK_STREAM and domain AF_INET
    """

    logging.info("using the socket fdmem = %d,fdrpc = %d,fdfs = %s",fdmem,fdrpc,fdfs)
    #Create socket mem ,rpc
    fd_mem = socket.fromfd(fdmem,socket.AF_INET,socket.SOCK_STREAM)
    
    fd_rpc = socket.fromfd(fdrpc,socket.AF_INET,socket.SOCK_STREAM)
    tool.util.set_cloexec(fdrpc)
    return connection(fd_mem,fd_rpc,fdfs)
