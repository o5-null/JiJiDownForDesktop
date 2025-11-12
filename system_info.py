import platform
import struct
import socket
import os
from pathlib import Path
from typing import Dict, Any, Optional


class SystemInfo:
    """系统信息工具类，提供统一的系统信息获取接口"""
    
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取完整的系统信息"""
        system = platform.system()
        machine = platform.machine()
        is_64bit = struct.calcsize("P") * 8 == 64
        is_arm = 'arm' in machine.lower() or 'aarch64' in machine.lower()
        
        return {
            'system': system,
            'machine': machine,
            'is_64bit': is_64bit,
            'is_arm': is_arm,
            'architecture': '64位' if is_64bit else '32位',
            'processor_type': 'ARM' if is_arm else 'x86',
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }
    
    def get_core_filename(self) -> str:
        """根据操作系统和架构返回对应的核心文件名"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # 判断系统架构
        is_64bit = struct.calcsize("P") * 8 == 64
        is_arm = 'arm' in machine or 'aarch64' in machine
        
        if system == 'windows':
            if is_64bit:
                return 'JiJiDownCore-win64.exe'
            else:
                return 'JiJiDownCore-win32.exe'
        elif system == 'darwin':  # macOS
            if is_arm:
                return 'JiJiDownCore-darwin-arm64'
            else:
                return 'JiJiDownCore-darwin-amd64'
        elif system == 'linux':
            if is_arm:
                return 'JiJiDownCore-linux-arm64'
            else:
                return 'JiJiDownCore-linux-amd64'
        else:
            # 默认返回Windows 64位版本
            return 'JiJiDownCore-win64.exe'
    
    def get_config_dir(self) -> Path:
        """获取配置目录路径"""
        system = platform.system()
        
        if system == 'Windows':
            config_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'JiJiDown'
        elif system == 'Darwin':  # macOS
            config_dir = Path.home() / '.config' / 'JiJiDown'
        else:  # Linux
            config_dir = Path.home() / '.config' / 'JiJiDown'
        
        return config_dir
    
    def get_default_paths(self) -> Dict[str, str]:
        """获取默认路径配置"""
        return {
            'temp_dir': str(Path('./TEMP').absolute()),
            'download_dir': str(Path('./Download').absolute()),
            'config_dir': str(self.get_config_dir()),
            'logs_dir': str(Path('./logs').absolute()),
            'resources_dir': str(Path('./resources').absolute())
        }
    
    def get_system_type(self) -> str:
        """获取系统类型"""
        return platform.system()
    
    def is_windows(self) -> bool:
        """是否为Windows系统"""
        return platform.system() == 'Windows'
    
    def is_macos(self) -> bool:
        """是否为macOS系统"""
        return platform.system() == 'Darwin'
    
    def is_linux(self) -> bool:
        """是否为Linux系统"""
        return platform.system() == 'Linux'
    
    def is_64bit(self) -> bool:
        """是否为64位系统"""
        return struct.calcsize("P") * 8 == 64
    
    def is_arm(self) -> bool:
        """是否为ARM架构"""
        machine = platform.machine().lower()
        return 'arm' in machine or 'aarch64' in machine
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()


# 创建全局系统信息实例
system_info = SystemInfo()