import sys

def halo_error(str):
    sys.stderr.write(str + "\n")
    sys.exit(1)
