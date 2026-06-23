import os
import sys
import subprocess
import time
import webbrowser

def install_deps():
    try:
        import radon
        print("[+] Dependency 'radon' is already installed.")
    except ImportError:
        print("[-] Dependency 'radon' not found. Installing now...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "radon"])
            print("[+] Successfully installed 'radon'.")
        except Exception as e:
            print(f"[-] Error installing dependency: {e}")
            print("Please make sure you have internet access and write permissions, or run: pip install radon manually.")
            sys.exit(1)

def main():
    print("="*60)
    print("             ULTRON COGNITIVE SYSTEM LAUNCHER")
    print("="*60)
    
    install_deps()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(script_dir, "ultron", "interfaces", "server.py")
    
    if not os.path.exists(server_script):
        print(f"[-] Error: Server script not found at {server_script}")
        sys.exit(1)
        
    print("[+] Starting background server...")
    
    # Start the server subprocess
    # Run with current python executable
    proc = subprocess.Popen(
        [sys.executable, server_script],
        cwd=script_dir
    )
    
    print("[+] Waiting for server to initialize...")
    time.sleep(1.5) # Wait for socket to bind
    
    print("[+] Launching system web browser...")
    webbrowser.open("http://localhost:8000")
    
    print("\n[+] Ultron is running!")
    print("    * Web Dashboard: http://localhost:8000")
    print("    * To shut down, press CTRL+C or Enter.\n")
    
    try:
        # Simple cross-platform wait
        input("Press Enter to stop the server...\n")
    except KeyboardInterrupt:
        print("\n[-] Shutdown signal received via KeyboardInterrupt.")
    except Exception:
        pass
        
    print("[-] Terminating background server...")
    proc.terminate()
    try:
        proc.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        print("[-] Force killing background server...")
        proc.kill()
        
    print("[+] Clean shutdown complete.")

if __name__ == "__main__":
    main()
