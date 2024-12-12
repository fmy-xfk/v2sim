import sys
from feasytools import ArgChecker
from flocale import Lang
from ftrafficgen import TrafficGenerator


def print_help(err:str = ""):
    if err != "":
        print(err)
    print(Lang.CSGEN_HELP_STR.format(sys.argv[0]))
    sys.exit()

if __name__ == "__main__":
    params = ArgChecker()
    if params.pop_bool("h") or params.pop_bool("help"):
        print_help()

    try:
        root = params.pop_str("d")
    except:
        print_help(Lang.ERROR_CMD_NOT_SPECIFIED.format("d"))
    
    TrafficGenerator(root).CSFromArgs(params)