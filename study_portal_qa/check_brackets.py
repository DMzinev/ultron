import os, re

base = r'c:\Users\This PC\Desktop\cost accounting'
js_files = []
for d in ['controllers', 'domain', 'cognitive', 'ui', 'storage', 'utilities']:
    dp = os.path.join(base, d)
    if os.path.isdir(dp):
        for f in os.listdir(dp):
            if f.endswith('.js'):
                js_files.append(os.path.join(dp, f))

def check_brackets(fp):
    with open(fp, encoding='utf-8') as f:
        content = f.read()
    
    # Remove single line comments
    content = re.sub(r'//.*', '', content)
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove template literals (backticks). Note: this doesn't handle nested `${}` with backticks properly, but it's an approximation.
    content = re.sub(r'`[^`]*`', '', content)
    
    # Remove strings
    content = re.sub(r"'[^']*'", '', content)
    content = re.sub(r'"[^"]*"', '', content)
    
    braces = content.count('{') - content.count('}')
    parens = content.count('(') - content.count(')')
    brackets = content.count('[') - content.count(']')
    
    issues = []
    if braces != 0: issues.append(f'braces:{braces:+d}')
    if parens != 0: issues.append(f'parens:{parens:+d}')
    if brackets != 0: issues.append(f'brackets:{brackets:+d}')
    if issues:
        print(f'{os.path.basename(fp)}: ' + ', '.join(issues))
    else:
        print(f'{os.path.basename(fp)}: OK')

for fp in js_files:
    check_brackets(fp)
