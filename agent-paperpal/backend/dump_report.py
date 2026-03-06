with open('validate_report.txt', 'r', encoding='utf-8', errors='replace') as f:
    for i, line in enumerate(f):
        if line.strip():
            print(f"{i}: {line.strip()}")
