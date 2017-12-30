#!/usr/bin/python3

import sys, json

stack=[]
with open(str(sys.argv[1]),"r", encoding="utf-8") as f:
    for i in f:
        stack.append(i[:-1])
    
    json.dump(stack, sys.stdout)
