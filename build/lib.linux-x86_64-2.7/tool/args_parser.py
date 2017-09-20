import argparse

def docker_migrate_service_parse():
    """ Parse docker migrate service Command args"""
    parser = argparse.ArgumentParser("Open docker migrate service!")
    parser.add_argument("--fdrpc",type=int,required=True,help="RPC Socket File Descriptor")
    parser.add_argument("--fdmem",type=int,required=True,help="Memory Socket File Descriptor")
    parser.add_argument("--fdfs",type=int,required=True,help="Module specific definition of fs channel")
    parser.add_argument("--log-file",type=int,required=True,help="The logfile path to write log")

    return parser.parse_args()

