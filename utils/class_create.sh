#!/bin/bash

cat $1 | grep class | awk '{ print $2 '} | cut -d'(' -f1 > temp_class
./class_create.py $1
