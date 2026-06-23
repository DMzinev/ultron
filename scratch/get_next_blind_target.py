import subprocess
import os
import sys

def main():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    proc = subprocess.Popen(
        [sys.executable, "-u", "ultron/blind_rate.py", repo_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    buffer = ""
    target_file = None
    while True:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
        if "Enter Rater ID:" in buffer:
            break
            
    proc.terminate()
    proc.wait()
    
    for line in buffer.splitlines():
        if "BLIND RATING TARGET:" in line:
            target_file = line.split("BLIND RATING TARGET:")[-1].strip()
            break
            
    if target_file:
        print(f"TARGET_FILE:{target_file}")
    else:
        print("NO_TARGET_FOUND")

if __name__ == "__main__":
    main()
