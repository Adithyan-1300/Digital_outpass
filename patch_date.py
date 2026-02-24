import glob
import re
import os

for file_path in glob.glob("backend/routes/*.py"):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to insert:
    # if 'return_date' in item and item['return_date']: item['return_date'] = format_date(item['return_date'])
    # right after format_date(item['out_date'])
    
    def replacement(m):
        indent = m.group(1)
        var_name = m.group(2)
        original = f"{indent}{var_name}['out_date'] = format_date({var_name}['out_date'])"
        addition = f"{indent}if 'return_date' in {var_name} and {var_name}['return_date']:{indent}    {var_name}['return_date'] = format_date({var_name}['return_date'])"
        return original + addition

    new_content = re.sub(
        r"(\s+)([a-zA-Z_]+)\['out_date'\]\s*=\s*format_date\(\2\['out_date'\]\)",
        replacement,
        content
    )
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Patched {file_path}")
