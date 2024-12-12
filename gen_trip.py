import sys
from flocale import Lang
from ftrafficgen import TrafficGenerator, DEFAULT_CNAME
from feasytools import ArgChecker
from feasytools.argchk import KeyNotSpecifiedError

def print_help():
    print(Lang.TRIPGEN_HELP_STR.format(sys.argv[0],DEFAULT_CNAME))
    sys.exit()

if __name__ == "__main__":
    params = ArgChecker()
    if params.pop_bool("h"):
        print_help()
        
    try:
        pname = params.pop_str("d")
    except:
        print(Lang.ERROR_SUMO_CONFIG_NOT_SPECIFIED)
        print_help()
    try:
        TrafficGenerator(pname).EVTripsFromArgs(params)
    except KeyNotSpecifiedError as e:
        print(Lang.ERROR_SUMO_N_VEH_NOT_SPECIFIED)
        print_help()