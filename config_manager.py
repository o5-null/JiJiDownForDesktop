import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
from loguru import logger
from system_info import system_info


# 辅助函数
def ensure_dir(path: str) -> str:
    """确保目录存在，如果不存在则创建"""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return str(path_obj)

def find_executable(name: str) -> Optional[str]:
    """查找可执行文件路径"""
    try:
        import shutil
        return shutil.which(name)
    except ImportError:
        return None


class ConfigManager:
    """配置文件管理器"""
    
    # 配置项定义模式 - 统一配置访问
    CONFIG_SCHEMA = {
        'download_dir': {
            'path': 'download-task.download-dir',
            'default': lambda: str(Path('./Download').resolve()),
            'description': '下载目录'
        },
        'temp_dir': {
            'path': 'download-task.temp-dir', 
            'default': lambda: str(Path('./TEMP').resolve()),
            'post_processor': lambda path: ensure_dir(path),
            'description': '临时目录'
        },
        'ffmpeg_path': {
            'path': 'download-task.ffmpeg-path',
            'default': lambda: find_executable('ffmpeg') or '',
            'description': 'FFmpeg路径'
        },
        'log_level': {
            'path': 'log-level',
            'default': 'info',
            'validator': lambda x: x in ['info', 'warning', 'error', 'debug', 'silent'],
            'description': '日志级别'
        },
        'max_task': {
            'path': 'download-task.max-task',
            'default': 2,
            'validator': lambda x: 1 <= x <= 5,
            'normalizer': lambda x: max(1, min(5, x)),
            'description': '最大同时下载任务数'
        },
        'download_speed_limit': {
            'path': 'download-task.download-speed-limit',
            'default': 0,
            'validator': lambda x: 0 <= x <= 1048576,
            'description': '下载速度限制'
        },
        'user_info': {
            'path': 'user-info',
            'default': dict,
            'description': '用户信息'
        },
        'external_ports': {
            'path': 'external-controller-port',
            'default': lambda: {
                'grpc': 4000,
                'grpc-web': 4100,
                'restful-api': 64001
            },
            'validator': lambda ports: (
                isinstance(ports, dict) and
                all(isinstance(p, int) for p in ports.values()) and
                # gRPC端口验证 (1024-49151或0)
                (ports.get('grpc', 0) == 0 or 1024 <= ports.get('grpc', 0) <= 49151) and
                # gRPC-Web端口验证 (1024-49151或0)
                (ports.get('grpc-web', 0) == 0 or 1024 <= ports.get('grpc-web', 0) <= 49151) and
                # RESTful API端口验证 (固定64001)
                ports.get('restful-api', 0) == 64001
            ),
            'description': '外部控制器端口配置'
        }
    }
    
    def __init__(self):
        self.config_data = {}
        self.config_file_path = None
        self.default_config = self._get_default_config()
        # 缓存配置值以避免重复计算
        self._config_cache = {}
    
    def get_config(self, config_key: str, use_cache: bool = True) -> Any:
        """
        统一配置访问方法 - 替代所有单独的get_xxx方法
        
        Args:
            config_key: 配置项键名，对应CONFIG_SCHEMA中的键
            use_cache: 是否使用缓存
            
        Returns:
            配置值
        """
        if use_cache and config_key in self._config_cache:
            return self._config_cache[config_key]
        
        if config_key not in self.CONFIG_SCHEMA:
            logger.warning(f"未知的配置项: {config_key}")
            return None
        
        schema = self.CONFIG_SCHEMA[config_key]
        config_path = schema['path']
        
        # 获取配置值
        value = self.get(config_path)
        
        # 如果没有设置配置值，使用默认值
        if value is None:
            default_value = schema['default']
            # 如果默认值是可调用对象，调用它获取实际值
            if callable(default_value):
                try:
                    value = default_value()
                    logger.info(f"配置项 {config_key} 使用默认值: {value}")
                except Exception as e:
                    logger.error(f"获取配置项 {config_key} 默认值失败: {e}")
                    value = None
            else:
                value = default_value
        
        # 验证配置值
        validator = schema.get('validator')
        if validator and value is not None:
            if not validator(value):
                logger.warning(f"配置项 {config_key} 的值 {value} 未通过验证，使用默认值")
                # 重新获取默认值
                default_value = schema['default']
                if callable(default_value):
                    value = default_value()
                else:
                    value = default_value
        
        # 标准化配置值
        normalizer = schema.get('normalizer')
        if normalizer and value is not None:
            value = normalizer(value)
        
        # 后处理配置值
        post_processor = schema.get('post_processor')
        if post_processor and value is not None:
            try:
                value = post_processor(value)
            except Exception as e:
                logger.error(f"配置项 {config_key} 后处理失败: {e}")
        
        # 缓存结果
        if use_cache:
            self._config_cache[config_key] = value
        
        return value
    
    def set_config(self, config_key: str, value: Any) -> None:
        """
        统一配置设置方法 - 替代所有单独的set_xxx方法
        
        Args:
            config_key: 配置项键名，对应CONFIG_SCHEMA中的键
            value: 要设置的值
        """
        if config_key not in self.CONFIG_SCHEMA:
            logger.warning(f"未知的配置项: {config_key}")
            return
        
        schema = self.CONFIG_SCHEMA[config_key]
        config_path = schema['path']
        
        # 清除缓存
        if config_key in self._config_cache:
            del self._config_cache[config_key]
        
        # 设置配置值
        self.set(config_path, value)
        logger.info(f"配置项 {config_key} 已设置为: {value}")
    
    def clear_cache(self) -> None:
        """清除配置缓存"""
        self._config_cache.clear()
        logger.debug("配置缓存已清除")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'log-level': 'info',
            'external-controller-port': {
                'grpc': 4000,
                'grpc-web': 4100,
                'restful-api': 64001
            },
            'user-info': {
                'access-token': '',
                'refresh-token': '',
                'cookies': '',
                'raw-access-token': '',
                'raw-cookies': '',
                'hide-nickname': False
            },
            'download-task': {
                'temp-dir': system_info.get_default_paths()['temp_dir'],
                'download-dir': system_info.get_default_paths()['download_dir'],
                'ffmpeg-path': '',
                'max-task': 2,
                'download-speed-limit': 0,
                'disable-mcdn': False
            },
            'jdm-settings': {
                'max-retry': 3,
                'retry-wait': 5,
                'session-workers': 4,
                'part-workers': 4,
                'min-split-size': 1048576,
                'proxy-addr': '',
                'check-best-mirror': True,
                'cache-in-ram': False,
                'cache-in-ram-limit': 536870912,
                'insecure-skip-verify': False,
                'custom-root-certificates': ''
            }
        }
    
    def get_config_dir(self) -> Path:
        """获取配置目录路径"""
        config_dir = system_info.get_config_dir()
        # 确保配置目录存在
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def get_config_file_path(self) -> Path:
        """获取配置文件路径"""
        return self.get_config_dir() / 'config.yaml'
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
            
        Returns:
            配置数据字典
        """
        if config_path:
            config_file = Path(config_path)
        else:
            config_file = self.get_config_file_path()
            
        self.config_file_path = config_file
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.config_data = yaml.safe_load(f) or {}
                
                # 合并默认配置，确保所有必需的键都存在
                self.config_data = self._merge_with_defaults(self.config_data)
                logger.info(f"配置文件加载成功: {config_file}")
            else:
                # 如果配置文件不存在，使用默认配置并设置默认下载路径
                self.config_data = self.default_config.copy()
                logger.info(f"配置文件不存在，使用默认配置: {config_file}")
                
        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            self.config_data = self.default_config.copy()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config_data = self.default_config.copy()
            
        return self.config_data.copy()
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """将用户配置与默认配置合并"""
        merged = self.default_config.copy()
        self._deep_merge(merged, config)
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_config(self, config_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存配置文件
        
        Args:
            config_data: 要保存的配置数据，如果为None则使用当前配置
            
        Returns:
            是否保存成功
        """
        if config_data:
            self.config_data = config_data
            
        if not self.config_file_path:
            self.config_file_path = self.get_config_file_path()
            
        try:
            # 确保配置目录存在
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存配置文件
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                
            logger.success(f"配置文件保存成功: {self.config_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 键路径，用点号分隔，如 'download-task.max-task'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key_path: 键路径，用点号分隔，如 'download-task.max-task'
            value: 要设置的值
        """
        keys = key_path.split('.')
        target = self.config_data
        
        # 遍历到倒数第二个键
        for key in keys[:-1]:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            target = target[key]
            
        # 设置最终值
        target[keys[-1]] = value
    
    # 以下是兼容旧代码的方法，现在都是get_config的包装器
    def get_download_dir(self) -> str:
        """获取下载目录"""
        return self.get_config('download_dir')
    
    def get_temp_dir(self) -> str:
        """获取临时目录"""
        return self.get_config('temp_dir')
    
    def get_ffmpeg_path(self) -> str:
        """获取FFmpeg路径"""
        return self.get_config('ffmpeg_path')
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.get_config('log_level')
    
    def get_max_task(self) -> int:
        """获取最大任务数"""
        return self.get_config('max_task')
    
    def get_download_speed_limit(self) -> int:
        """获取下载速度限制"""
        return self.get_config('download_speed_limit')
    
    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        return self.get_config('user_info')
    
    def set_user_info(self, user_info: Dict[str, Any]) -> None:
        """设置用户信息"""
        self.set_config('user_info', user_info)
    
    def get_external_ports(self) -> Dict[str, int]:
        """获取外部控制器端口配置"""
        return self.get_config('external_ports')
    
    def validate_config(self) -> Dict[str, Any]:
        """
        验证配置有效性
        
        Returns:
            验证结果 {'valid': bool, 'errors': list}
        """
        errors = []
        
        # 验证日志级别
        log_level = self.get_log_level()
        valid_log_levels = ['info', 'warning', 'error', 'debug', 'silent']
        if log_level not in valid_log_levels:
            errors.append(f"无效的日志级别: {log_level}")
        
        # 验证最大任务数
        max_task = self.get_max_task()
        if not 1 <= max_task <= 5:
            errors.append(f"最大任务数必须在1-5之间: {max_task}")
        
        # 验证下载速度限制
        speed_limit = self.get_download_speed_limit()
        if speed_limit < 0 or speed_limit > 1048576:
            errors.append(f"下载速度限制必须在0-1048576之间: {speed_limit}")
        
        # 验证端口配置
        ports = self.get_external_ports()
        for port_name, port_value in ports.items():
            if port_value != 0 and not 1024 <= port_value <= 49151:
                errors.append(f"{port_name}端口必须在1024-49151之间或设为0: {port_value}")
        
        # 验证路径
        temp_dir = self.get_temp_dir()
        if temp_dir and not Path(temp_dir).parent.exists():
            errors.append(f"临时目录父目录不存在: {Path(temp_dir).parent}")
            
        download_dir = self.get_download_dir()
        if download_dir and not Path(download_dir).parent.exists():
            errors.append(f"下载目录父目录不存在: {Path(download_dir).parent}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def export_config(self, export_path: str) -> bool:
        """
        导出配置到指定路径
        
        Args:
            export_path: 导出路径
            
        Returns:
            是否导出成功
        """
        try:
            export_file = Path(export_path)
            with open(export_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return True
        except Exception as e:
            logger.error(f"导出配置文件失败: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """
        从指定路径导入配置
        
        Args:
            import_path: 导入路径
            
        Returns:
            是否导入成功
        """
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                return False
                
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_config = yaml.safe_load(f) or {}
            
            # 合并配置
            self.config_data = self._merge_with_defaults(imported_config)
            return True
            
        except Exception as e:
            logger.error(f"导入配置文件失败: {e}")
            return False
    
    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config_data = self.default_config.copy()
        self.save_config()
        logger.info("配置已重置为默认值")


# 创建全局配置管理器实例
config_manager = ConfigManager()