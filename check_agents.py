import shutil
import sys

def check_agent(name, command):
    path = shutil.which(command)
    if path:
        print(f"✅ 发现 {name} 智能体，安装路径: {path}")
        return True
    else:
        print(f"❌ 未发现 {name} 智能体 (命令 '{command}' 不在 PATH 中)")
        return False

def main():
    print("开始检测本机智能体安装情况...\n")
    
    openclaw_installed = check_agent("OpenClaw", "openclaw")
    hermes_installed = check_agent("Hermes", "hermes")
    
    print("\n检测完成。")
    if not (openclaw_installed or hermes_installed):
        print("提示: 未检测到支持的智能体。请确保它们已正确安装并且命令在系统的 PATH 环境变量中。")

if __name__ == "__main__":
    main()
