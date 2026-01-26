#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HajimiRef 一键构建脚本
使用方法: python build.py
"""

import os
import sys
import shutil
import subprocess

def main():
    print("=" * 40)
    print("   HajimiRef 一键构建脚本")
    print("=" * 40)
    print()

    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 1. 清理旧的构建文件
    print("[1/3] 清理旧的构建文件...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    print("      完成！")
    print()

    # 2. 开始构建
    print("[2/3] 开始打包 (请耐心等待)...")
    print()
    
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "HajimiRef.spec", "--noconfirm"],
        shell=False
    )

    # 3. 检查构建结果
    print()
    exe_path = os.path.join("dist", "HajimiRef.exe")
    
    if os.path.exists(exe_path):
        print("[3/3] 构建成功！")
        print()
        print("=" * 40)
        print(f"   输出文件: {os.path.abspath(exe_path)}")
        print("=" * 40)
        
        # 打开输出目录
        if sys.platform == "win32":
            os.startfile(os.path.join(script_dir, "dist"))
    else:
        print("[3/3] 构建失败，请检查错误信息！")
        return 1

    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        input("\n按回车键退出...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户取消构建")
        sys.exit(1)
    except Exception as e:
        print(f"\n构建出错: {e}")
        input("\n按回车键退出...")
        sys.exit(1)
