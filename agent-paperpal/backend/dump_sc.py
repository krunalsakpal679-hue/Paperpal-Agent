with open('validate_report.txt', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
    for l in lines:
        if "SC-" in l or "PASS" in l or "FAIL" in l:
            print(l.strip())
