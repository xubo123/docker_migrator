import argparse
import client.iters
import client.img_migrator
import tool.criu_api
def docker_migrate_service_parse():
    """ Parse docker migrate service Command args"""
    parser = argparse.ArgumentParser("Open docker migrate service!")
    parser.add_argument("--fdrpc", type=int, required=True, help="RPC Socket File Descriptor")
    parser.add_argument("--fdmem", type=int, required=True, help="Memory Socket File Descriptor")
    parser.add_argument("--fdfs", help="Module specific definition of fs channel")
    parser.add_argument("--log-file", help="The logfile path to write log")

    return parser.parse_args()

def docker_migrate_client_parse():
    """Parse docker migrate client cmd args"""

    parser = argparse.ArgumentParser("Client to implement docker live migration")
    parser.add_argument("ct_id", help = "ID of which container to migrate!")
    parser.add_argument("--to", help = "IP of where to migrate!")
    parser.add_argument("--fs-driver", type=str, default="aufs", help="fs_driver to migrate")
    parser.add_argument("--fdmem", type=int, required=True, help="socket fd to transmit memory data!")
    parser.add_argument("--fdrpc", type=int, required=True, help="socket fd to send rpc require data!")
    parser.add_argument("--fdfs", help="socket fd to send fs data!")
    parser.add_argument("--mode", choices=client.iters.MIGRATION_MODES, default=client.iters.MIGRATION_MODE_LIVE, help="Mode of migration")
    parser.add_argument("--log-file", help="Write logging messages to specified file")
    parser.add_argument("--force", default=False, action='store_true', help="Don't do any sanity checks")
    parser.add_argument("--skip-cpu-check", default=False, action='store_true', help="Skip CPU compatibility check")
    parser.add_argument('--pre-dump',dest='pre_dump', action='store_const', const=client.iters.PRE_DUMP_ENABLE, help='Force enable pre-dumps')
    parser.add_argument("--skip-criu-check", default=False, action='store_true', help="Skip criu compatibility check")
    parser.add_argument("--keep-images", default=False, action='store_true', help="Keep images after migration")
    parser.add_argument("--img-path", default=client.img_migrator.def_path, help="Directory where to put images")
    parser.add_argument("-v", default=tool.criu_api.def_verb, type=int, dest="verbose", help="Verbosity level")
    parser.add_argument("-j", "--shell-job", default=False, action='store_true', help="Allow migration of shell jobs")
    return parser.parse_args()
