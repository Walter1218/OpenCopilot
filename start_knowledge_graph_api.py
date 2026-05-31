#!/usr/bin/env python3
"""
启动知识图谱 API 服务器

用法:
    python start_knowledge_graph_api.py [--host HOST] [--port PORT] [--project-root PROJECT_ROOT]

示例:
    python start_knowledge_graph_api.py
    python start_knowledge_graph_api.py --port 8091
    python start_knowledge_graph_api.py --project-root /path/to/project
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from knowledge_graph import start_api_server


def main():
    parser = argparse.ArgumentParser(description="启动知识图谱 API 服务器")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8090, help="服务器端口 (默认: 8090)")
    parser.add_argument("--project-root", default=str(project_root), help="项目根目录路径")
    
    args = parser.parse_args()
    
    print(f"启动知识图谱 API 服务器...")
    print(f"主机: {args.host}")
    print(f"端口: {args.port}")
    print(f"项目根目录: {args.project_root}")
    print(f"API 文档: http://{args.host}:{args.port}/docs")
    print(f"健康检查: http://{args.host}:{args.port}/health")
    print()
    
    try:
        start_api_server(
            host=args.host,
            port=args.port,
            project_root=args.project_root
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()