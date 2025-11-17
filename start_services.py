import os
import time
import subprocess
import sys
import socket

os.environ['TTS_BATCH_SIZE'] = '2'

def fix_encoding():
    """Fix encoding issues for surreal_commands"""
    # Set environment variables
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Reconfigure standard output
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

fix_encoding()

def is_port_open(port, host='localhost', timeout=1):
    """Check if a port is open"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

def wait_for_port(port, timeout=30):
    """Wait for port to become available"""
    print(f"Waiting for port {port} to open...")
    for i in range(timeout):
        if is_port_open(port):
            print(f"✅ Port {port} is now open")
            return True
        time.sleep(1)
    print(f"⚠️  Warning: Port {port} did not open within {timeout} seconds")
    return False

def run_command(command, cwd=None, shell=False):
    """Helper function to run commands"""
    try:
        if sys.platform == "win32":
            # Use shell=True on Windows
            result = subprocess.run(command, shell=True, cwd=cwd, check=True)
        else:
            result = subprocess.run(command, shell=shell, cwd=cwd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command execution failed: {e}")
        return False
    except FileNotFoundError as e:
        print(f"❌ Command not found: {e}")
        return False

def main():
    print("🚀 Starting Open Notebook (Database + API + Worker + Frontend)...")
    
    # Start SurrealDB
    print("📊 Starting SurrealDB...")
    run_command(["docker", "compose", "up", "-d", "surrealdb"])
    time.sleep(5)
    
    # Start API
    print("🔧 Starting API backend...")
    if sys.platform == "win32":
        # Use start command to run in background on Windows
        subprocess.Popen("uv run run_api.py", shell=True, stdout=open("api.log", "w"), stderr=subprocess.STDOUT)
    else:
        subprocess.Popen(["nohup", "uv", "run", "run_api.py"], stdout=open("api.log", "w"), stderr=subprocess.STDOUT)
    
    # Wait for API to start
    if not wait_for_port(5055):
        print("❌ API startup failed, please check api.log file")
        return
    
    # Start Worker
    print("⚙️ Starting background worker...")
    if sys.platform == "win32":
        subprocess.Popen(
            "uv run --env-file .env surreal-commands-worker --import-modules commands", 
            shell=True, 
            stdout=open("worker.log", "w"), 
            stderr=subprocess.STDOUT
        )
    else:
        subprocess.Popen([
            "nohup", "uv", "run", "--env-file", ".env", "surreal-commands-worker", 
            "--import-modules", "commands"
        ], stdout=open("worker.log", "w"), stderr=subprocess.STDOUT)
    
    time.sleep(2)
    
    print("🌐 Starting Next.js frontend...")
    print("✅ All services started!")
    print("📱 Frontend: http://localhost:3000")
    print("🔗 API: http://localhost:5055")
    print("📚 API Docs: http://localhost:5055/docs")
    
    # Start frontend - using correct command format
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    if not os.path.exists(frontend_dir):
        print(f"❌ Frontend directory does not exist: {frontend_dir}")
        return
    
    try:
        if sys.platform == "win32":
            # Use npm.cmd on Windows
            subprocess.run("npm run dev", shell=True, cwd=frontend_dir, check=True)
        else:
            # Use npm directly on Linux/Mac
            subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Frontend service interrupted by user")
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        print("💡 Please ensure Node.js and npm are installed, and run 'npm install' in the frontend directory")

if __name__ == "__main__":
    main()