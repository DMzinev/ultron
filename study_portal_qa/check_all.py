import os
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, ".."))
esbuild_path = os.path.join(root_dir, "package", "esbuild.exe")

errors = 0
for r, dirs, fs in os.walk(root_dir):
    # Skip unrelated directories
    dirs[:] = [d for d in dirs if d not in ('.git', '.synapse', 'node_modules', 'synapse_project', 'ultron', 'study_portal_qa', 'study_materials', 'scratch')]
    for f in fs:
        if f.endswith('.js'):
            p = os.path.join(r, f)
            res = subprocess.run([esbuild_path, p], capture_output=True, text=True)
            if res.returncode != 0:
                print(f'ERROR IN {p}:\n{res.stderr}')
                errors += 1

if errors == 0:
    print('All JS files are syntactically valid.')
else:
    print(f'Verification complete. Found {errors} error(s).')
