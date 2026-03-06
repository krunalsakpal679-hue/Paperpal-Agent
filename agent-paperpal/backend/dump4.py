import json
with open('validate_err_cmd2.txt', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
    
with open('trace.json', 'w') as f:
    json.dump([l.strip() for l in lines[-40:]], f)
