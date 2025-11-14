import os
import time
import subprocess
import sys
import socket

def fix_encoding():
    """修复 surreal_commands 的编码问题"""
    # 设置环境变量
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # 重新配置标准输出
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

fix_encoding()

def is_port_open(port, host='localhost', timeout=1):
    """检查端口是否开放"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

def wait_for_port(port, timeout=30):
    """等待端口开放"""
    print(f"等待端口 {port} 开放...")
    for i in range(timeout):
        if is_port_open(port):
            print(f"✅ 端口 {port} 已开放")
            return True
        time.sleep(1)
    print(f"⚠️  警告: 端口 {port} 在 {timeout} 秒内未开放")
    return False

def run_command(command, cwd=None, shell=False):
    """运行命令的辅助函数"""
    try:
        if sys.platform == "win32":
            # 在 Windows 上使用 shell=True
            result = subprocess.run(command, shell=True, cwd=cwd, check=True)
        else:
            result = subprocess.run(command, shell=shell, cwd=cwd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        return False
    except FileNotFoundError as e:
        print(f"❌ 找不到命令: {e}")
        return False

def main():
    print("🚀 Starting Open Notebook (Database + API + Worker + Frontend)...")
    
    # 启动 SurrealDB
    print("📊 Starting SurrealDB...")
    run_command(["docker", "compose", "up", "-d", "surrealdb"])
    time.sleep(5)
    
    # 启动 API
    print("🔧 Starting API backend...")
    if sys.platform == "win32":
        # Windows 使用 start 命令后台运行
        subprocess.Popen("uv run run_api.py", shell=True, stdout=open("api.log", "w"), stderr=subprocess.STDOUT)
    else:
        subprocess.Popen(["nohup", "uv", "run", "run_api.py"], stdout=open("api.log", "w"), stderr=subprocess.STDOUT)
    
    # 等待 API 启动
    if not wait_for_port(5055):
        print("❌ API 启动失败，请检查 api.log 文件")
        return
    
    # 启动 Worker
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
    
    # 启动前端 - 使用正确的命令格式
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    if not os.path.exists(frontend_dir):
        print(f"❌ 前端目录不存在: {frontend_dir}")
        return
    
    try:
        if sys.platform == "win32":
            # Windows 上使用 npm.cmd
            subprocess.run("npm run dev", shell=True, cwd=frontend_dir, check=True)
        else:
            # Linux/Mac 上直接使用 npm
            subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        print("\n🛑 用户中断了前端服务")
    except Exception as e:
        print(f"❌ 启动前端失败: {e}")
        print("💡 请确保已安装 Node.js 和 npm，并在 frontend 目录中运行 'npm install'")

if __name__ == "__main__":
    main()