import sys

with open('validate_err_cmd.txt', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
    print(text[-2000:])
