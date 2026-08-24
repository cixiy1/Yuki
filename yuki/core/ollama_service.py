import subprocess
import socket
import sys
import time
from typing import Optional

ollama_proc: Optional[subprocess.Popen] = None


def is_ollama_running(host="127.0.0.1", port=11434, timeout: float = 1) -> bool:
    """检测Ollama服务是否正在运行"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def start_ollama_service():
    """后台唤醒启动 ollama serve"""
    if is_ollama_running():
        print("Ollama 服务已运行，无需启动")
        return True

    print("未检测到Ollama服务，正在启动...")
    global ollama_proc
    creationflags = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    ollama_proc = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **creationflags,
    )
    time.sleep(2)  # 等待服务初始化
    print("Ollama 服务已启动")
    return True


def stop_ollama_service():
    global ollama_proc
    if ollama_proc is None:
        return
    print("正在关闭Ollama服务...")
    # 优雅终止
    ollama_proc.terminate()
    try:
        ollama_proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        # 超时强制杀死
        ollama_proc.kill()
        ollama_proc.wait()
    ollama_proc = None
    print("Ollama服务已关闭")
    return True
