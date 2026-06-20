import os
import sys

def analyze(file_path):
    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()
        
    depth_b = 0 # braces {}
    depth_p = 0 # parens ()
    depth_k = 0 # brackets []
    
    in_str = False
    str_char = ''
    in_comment = False
    in_block_comment = False
    
    for i, line in enumerate(lines):
        j = 0
        while j < len(line):
            c = line[j]
            if in_block_comment:
                if c == '*' and j+1 < len(line) and line[j+1] == '/':
                    in_block_comment = False
                    j += 1
            elif in_str:
                if c == '\\':
                    j += 1
                elif c == str_char:
                    in_str = False
            else:
                if c == '/' and j+1 < len(line) and line[j+1] == '/':
                    break
                elif c == '/' and j+1 < len(line) and line[j+1] == '*':
                    in_block_comment = True
                    j += 1
                elif c in ("'", '"', '`'):
                    in_str = True
                    str_char = c
                elif c == '{': depth_b += 1
                elif c == '}': depth_b -= 1
                elif c == '(': depth_p += 1
                elif c == ')': depth_p -= 1
                elif c == '[': depth_k += 1
                elif c == ']': depth_k -= 1
            j += 1
            
        if depth_p < 0 or depth_b < 0 or depth_k < 0:
            print(f"Negative depth at line {i+1}: braces={depth_b}, parens={depth_p}, brackets={depth_k}")
            print(line.strip())
            return
            
    print(f"Final depth: braces={depth_b}, parens={depth_p}, brackets={depth_k}")

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, ".."))
target_file = os.path.join(root_dir, "ui", "appUI_v2.js")

print(f"Analyzing {target_file}...")
analyze(target_file)
