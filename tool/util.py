import logging
import fcntl
import socket
import errno
import os

def log_uncaught_exception(type, value, traceback):
	logging.error(value, exc_info=(type, value, traceback))


def log_header():
	OFFSET_LINES_COUNT = 3
	for i in range(OFFSET_LINES_COUNT):
		logging.info("")

def set_cloexec(sk):
	flags = fcntl.fcntl(sk, fcntl.F_GETFD)
	fcntl.fcntl(sk, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
def makedirs(dirpath):
	try:
		os.makedirs(dirpath)
	except OSError as er:
		if er.errno == errno.EEXIST and os.path.isdir(dirpath):
			pass
		else:
			raise
