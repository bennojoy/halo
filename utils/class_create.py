#!/usr/bin/env python

import sys
import shlex
import optparse
import json

parser = optparse.OptionParser()
opts, args = parser.parse_args()
data = open("./temp_class").read().splitlines()
tmp = {}
for i in data:
    tmp[i] = args[0].split('.')[0]

print json.dumps(tmp, indent=3)
