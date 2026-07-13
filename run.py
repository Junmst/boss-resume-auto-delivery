# -*- coding: utf-8 -*-
"""BOSS自动投递工具 - 启动脚本"""
import os
import sys
import subprocess


def check_python():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"[错误] 需要 Python 3.8+, 当前版本: {sys.version}")
        sys.exit(1)
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")


def check_dependencies():
    """检查依赖包"""
    required = {
        "selenium": "4.10.0",
        "yaml": "6.0",
        "requests": "2.31.0",
    }
    missing = []
    for package, min_version in required.items():
        try:
            if package == "yaml":
                import yaml
            else:
                __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"[警告] 缺少依赖包: {', '.join(missing)}")
        print("正在尝试安装...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            )
            print("[OK] 依赖包安装完成")
        except Exception as e:
            print(f"[错误] 安装失败: {e}")
            print("请手动执行: pip install -r requirements.txt")
            sys.exit(1)
    else:
        print("[OK] 所有依赖包已就绪")


def main():
    """主启动函数"""
    print("=" * 60)
    print("  BOSS直聘自动投递工具 v1.0.0")
    print("=" * 60)

    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"[INFO] 工作目录: {os.getcwd()}")

    # 检查环境
    check_python()
    check_dependencies()

    # 运行主程序
    print("\n[INFO] 正在启动...\n")
    from src.main import main as run_main
    run_main()


if __name__ == "__main__":
    main()
