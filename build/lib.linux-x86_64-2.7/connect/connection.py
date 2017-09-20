import logging
import socket
import tool.util

class connection(object):
    """docker migrate service connection
    the Class include all socket fd info about data transmit
    """

    def _init_(self,fdmem,fdrpc,fdfs):
        self.fdmem = fdmem
        self.fdrpc = fdrpc
        self.fdfs = fdfs

    def close():
        self.fdmem.close()
        self.fdrpc.close()


def establish(fdmem,fdrpc,fdfs):
    """ Build socket from fd,And return the connection class wrapping the socket
        We build the socket with the type of SOCK_STREAM and domain AF_INET
    """

    logging.info("using the socket fdmem = %d,fdrpc = %d,fdfs = %d",fdmem,fdrpc,fdfs)

    #Create socket mem ,rpc
    fdmem = socket.fromfd(fdmem,AF_INET,SOCK_STREAM)
    
    fdrpc = socket.fromfd(fdrpc,AF_INET,SOCK_STREAM)
    util.set_cloexec(fdrpc)
    return connection(fdmem,fdrpc,fdfs)