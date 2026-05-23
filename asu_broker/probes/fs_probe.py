import asyncio
import os

async def read_file_as_context(file_path: str) -> str:
    """
    [预埋] 文件系统能力：跨越 IDE 沙盒读取特定路径的文件作为 AI 的上下文。
    由于 Broker 运行在终端原生权限下（甚至可以申请 Full Disk Access），
    它可以无缝读取 IDE 插件可能因为沙盒限制而无法读取的桌面或下载目录文件。
    """
    expanded_path = os.path.expanduser(file_path)
    if not os.path.exists(expanded_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")
        
    try:
        # 在真实的生产环境中应考虑大文件分块和编码问题
        with open(expanded_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"读取文件失败: {str(e)}")
