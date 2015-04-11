#!/usr/bin/env python

import sys
import shlex
import optparse
import json

parser = optparse.OptionParser()
opts, args = parser.parse_args()
data = open(args[0]).read().splitlines()
tmp = {}
inclass = False
inprops = False
props_tmp = {}
for i in data:
    if i.startswith('class'):
        class_name = i.split('(')[0].split()[1]
        inclass = True
        continue
    if 'props' in i:
        inprops = True
        props_tmp = {}
        continue
    if '    }' in i:
        inprops = False
        inclass = False
        if props_tmp.keys():
            tmp[class_name] = props_tmp
        continue
    if inclass and inprops:
        print i
        if '#' in i:
            continue
        else:
            props_tmp[i.split(':')[0].strip()] = i.split(':')[1].strip()



print json.dumps(tmp, indent=3)
