with open('validate_report.txt', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
    markers = ["SC-1", "SC-2", "SC-3", "SC-4", "SC-5"]
    for marker in markers:
        if marker in text:
            # Find the line
            for line in text.split('\n'):
                if marker in line and ("PASS" in line or "FAIL" in line):
                    print(line.strip())
