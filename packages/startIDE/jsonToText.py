#!/usr/bin/python3

import sys, json

with open(str(sys.argv[1]),"r", encoding="utf-8") as f:
    code=json.load(f)
    for i in code:
        print(i)
