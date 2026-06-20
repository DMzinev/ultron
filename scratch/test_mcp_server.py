import subprocess
import json
import sys
import time

def run_test():
    print("[+] Launching MCP Server...")
    proc = subprocess.Popen(
        [sys.executable, "ultron/mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a moment
    time.sleep(0.5)
    
    # 1. Send initialize
    print("[+] Sending initialize request...")
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
    }
    proc.stdin.write(json.dumps(init_msg) + "\n")
    proc.stdin.flush()
    
    res_line = proc.stdout.readline()
    print("[+] Received initialize response:")
    print(res_line.strip())
    
    # 2. Send tools/list
    print("[+] Sending tools/list request...")
    list_msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    proc.stdin.write(json.dumps(list_msg) + "\n")
    proc.stdin.flush()
    
    res_line = proc.stdout.readline()
    print("[+] Received tools/list response:")
    res_json = json.loads(res_line)
    print(json.dumps(res_json, indent=2))
    
    # 3. Call audit_file_anomalies tool
    print("[+] Sending tools/call request for audit_file_anomalies...")
    call_msg = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "audit_file_anomalies",
            "arguments": {
                "repo": "scratch/test_anomaly_dir",
                "target_file": "scratch/test_anomaly_dir/target_anomaly.py"
            }
        }
    }
    proc.stdin.write(json.dumps(call_msg) + "\n")
    proc.stdin.flush()
    
    res_line = proc.stdout.readline()
    print("[+] Received tools/call response:")
    res_json = json.loads(res_line)
    print(json.dumps(res_json, indent=2))
    
    # Terminate process
    proc.terminate()
    proc.wait()
    
    # Read errors from stderr if any
    stderr_out = proc.stderr.read()
    if stderr_out:
        print("[!] Server stderr:")
        print(stderr_out)

if __name__ == "__main__":
    run_test()
