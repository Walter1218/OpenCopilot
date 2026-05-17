import time
import logging
from logging.handlers import RotatingFileHandler
from pynput import mouse

# 配置日志记录：使用轮转文件处理器，限制单个文件大小并保留备份数
log_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# maxBytes=5*1024*1024 表示单个文件最大 5MB
# backupCount=3 表示最多保留 3 个历史备份文件 (mouse_tracking.log.1, mouse_tracking.log.2 等)
# 这样总日志占用空间最大被严格限制在约 20MB 以内
handler = RotatingFileHandler('mouse_tracking.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 节流控制：避免频繁写入导致 CPU 和磁盘 IO 占用过高
LAST_TIME = 0
THROTTLE_INTERVAL = 0.1  # 最小记录间隔（秒），例如 0.1 秒记录一次轨迹

def on_move(x, y):
    global LAST_TIME
    current_time = time.time()
    if current_time - LAST_TIME > THROTTLE_INTERVAL:
        logging.info(f"Move: ({x}, {y})")
        LAST_TIME = current_time

def on_click(x, y, button, pressed):
    action = "Pressed" if pressed else "Released"
    logging.info(f"Click: {action} {button} at ({x}, {y})")

def on_scroll(x, y, dx, dy):
    logging.info(f"Scroll: ({dx}, {dy}) at ({x}, {y})")

if __name__ == "__main__":
    print("🚀 后台鼠标轨迹监控已启动...")
    print("📂 实时数据正在写入当前目录的 'mouse_tracking.log' 文件。")
    print("⚠️  注意：在 macOS 上，首次运行需要授予终端“辅助功能(Accessibility)”权限。")
    print("🛑 按 Ctrl+C 停止监控。")
    
    try:
        # 使用 with 语句启动后台监听线程
        with mouse.Listener(
                on_move=on_move,
                on_click=on_click,
                on_scroll=on_scroll) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n⏹️ 监控已停止。")
