import traceback
import sys

with open('validate_err_cmd.txt', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
    for l in lines[-30:]:
        print(l.strip())
