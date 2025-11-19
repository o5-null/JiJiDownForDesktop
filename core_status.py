"""
核心状态管理模块
负责管理核心运行状态和全局缓存变量
"""

import time
from typing import Dict, Any
from loguru import logger
from core_manager import CoreManager

# 创建全局实例
core_manager = CoreManager()


# 创建全局缓存变量
core = {
    'exist': False,
    'filename': '',
    'path': '',
    'status': {
        'is_running': False,
        'process_exists': False,
        'process_status': 'unknown',
        'other_processes_running': False,
        'core_filename': '',
        'log_callbacks_count': 0,
        'last_update': None
    }
}


def update_core_status() -> bool:
    """
    更新全局缓存变量core中的核心运行状态
    
    Returns:
        bool: 更新是否成功
    """
    try:
        # 获取核心管理器状态
        core_status = core_manager.get_core_status()
        old_status = core['status']['is_running']
        # 获取核心文件信息
        core_info = core_manager.get_core_info()
        
        # 更新全局缓存变量
        core['exist'] = core_info['exist']
        core['filename'] = core_info['filename']
        core['path'] = core_info['path']
        
        # 更新状态信息
        core['status'].update({
            'is_running': core_status['is_running'],
            'process_exists': core_status['process_exists'],
            'process_status': core_status.get('process_status', 'unknown'),
            'other_processes_running': core_status.get('other_processes_running', False),
            'core_filename': core_status.get('core_filename', ''),
            'log_callbacks_count': core_status.get('log_callbacks_count', 0),
            'last_update': time.time()
        })
        if old_status != core['status']['is_running']:
            logger.debug(f"核心状态已更新: {core['status']}")
        return True
        
    except Exception as e:
        logger.error(f"更新核心状态失败: {str(e)}")
        return False


def get_core_status() -> Dict[str, Any]:
    """
    获取当前核心状态
    
    Returns:
        Dict[str, Any]: 核心状态信息
    """
    return core['status']


def is_core_running() -> bool:
    """
    检查核心是否正在运行
    
    Returns:
        bool: 核心是否正在运行
    """
    return core['status']['is_running']


def get_core_info() -> Dict[str, Any]:
    """
    获取核心文件信息
    
    Returns:
        Dict[str, Any]: 核心文件信息
    """
    return {
        'exist': core['exist'],
        'filename': core['filename'],
        'path': core['path']
    }