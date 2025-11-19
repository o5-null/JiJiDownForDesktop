"""
主程序入口模块
负责程序启动、配置初始化和路由设置
"""

import json
import pathlib
from nicegui import ui, app
from loguru import logger

from config_manager import config_manager
from system_info import system_info
from router import setup_routes


def initialize_config():
    """初始化配置"""
    # 创建必要的文件夹
    folders = ['./config', './TEMP', './downloads', './logs']
    for folder in folders:
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
    
    # 初始化配置管理器
    config_manager.initialize()
    
    # 初始化系统信息
    system_info.initialize()


def main():
    """主程序入口"""
    
    # 初始化配置
    initialize_config()
    
    # 设置路由
    setup_routes()
    
    # 设置UI启动参数
    ui.run(
        title='JiJiDown Desktop',
        favicon='🚀',
        port=8080,
        native=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()