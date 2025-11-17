import requests
import asyncio
from pathlib import Path
from typing import Optional, Callable
import time
import hashlib
import subprocess
import threading
from loguru import logger
from system_info import system_info

class CoreManager:
    def __init__(self):
        self.download_tasks = {}
        self.progress_callbacks = {}
        self.core_info = {
            'exist': False,
            'filename': '',
            'path': '',
            'system_info': {}
        }
        self.core_process = None
        self.is_running = False
        self.log_callbacks = []
    
    def get_system_info(self):
        """获取系统信息用于调试"""
        return system_info.get_system_info()
    
    def get_core_filename(self):
        """根据操作系统和架构返回对应的核心文件名"""
        return system_info.get_core_filename()
    
    def get_official_hash(self, filename: str) -> Optional[str]:
        """从官方获取文件的SHA256哈希值"""
        try:
            hash_url = "https://jj.紫灵.top/PC/ReWPF/core/JiJiDownCore-hash.txt"
            response = requests.get(hash_url, timeout=10)
            response.raise_for_status()
            
            # 解析hash文件内容
            hash_content = response.text
            for line in hash_content.split('\n'):
                line = line.strip()
                if '|' in line and filename in line:
                    parts = line.split('|')
                    if len(parts) >= 3 and parts[2].strip() == filename:
                        return parts[0].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"获取官方hash失败: {str(e)}")
            return None
        
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """计算文件的SHA256哈希值"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # 分块读取文件，避免大文件内存问题
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件hash失败: {str(e)}")
            return None
    
    def check_core_hash(self, resources_path: str = "./resources") -> dict:
        """检查核心文件的hash值是否匹配"""
        core_filename = self.get_core_filename()
        core_path = Path(resources_path).resolve() / core_filename
        
        logger.debug(f"开始检查核心文件hash: {core_filename}, 路径: {core_path}")
        
        if not core_path.exists():
            logger.warning(f"核心文件不存在: {core_path}")
            return {
                'valid': False,
                'exists': False,
                'message': '核心文件不存在'
            }
        
        # 获取官方hash值
        official_hash = self.get_official_hash(core_filename)
        hash_source = 'official'
        
        # 如果无法获取官方hash，使用备用hash
        
        if not official_hash:
            logger.error("无法获取在线hash值")
            return {
                'valid': False,
                'exists': True,
                'message': '无法获取官方hash值'
            }
        
        # 计算本地文件hash值
        local_hash = self.calculate_file_hash(str(core_path))
        if not local_hash:
            logger.error("无法计算本地文件hash值")
            return {
                'valid': False,
                'exists': True,
                'message': '无法计算本地文件hash值'
            }
        
        # 比较hash值
        is_valid = official_hash.lower() == local_hash.lower()
        
        if is_valid:
            logger.success(f"Hash校验通过: {core_filename}")
        else:
            logger.warning(f"Hash校验失败: {core_filename}, 官方hash: {official_hash}, 本地hash: {local_hash}")
        
        return {
            'valid': is_valid,
            'exists': True,
            'official_hash': official_hash,
            'local_hash': local_hash,
            'hash_source': hash_source,
            'message': 'Hash校验通过' if is_valid else 'Hash校验失败，文件可能已损坏或需要更新'
        }
    
    def check_core_exist(self, resources_path: str = "./resources"):
        """检查核心文件是否存在 - 已废弃，请使用check_core_hash()获取更详细的信息"""
        core_filename = self.get_core_filename()
        core_path = Path(resources_path).resolve() / core_filename
        
        # 更新核心信息
        self.core_info = {
            'exist': core_path.exists(),
            'filename': core_filename,
            'path': str(core_path),
            'system_info': self.get_system_info()
        }
        
        return self.core_info['exist']
    
    def get_core_info(self):
        """获取核心文件信息"""
        # 检查核心文件是否存在并更新信息
        self.check_core_exist()
        return self.core_info.copy()
    
    async def download_file(self, url: str, filename: str, save_path: str = "./resources", 
                          progress_callback: Optional[Callable] = None) -> dict:
        """
        异步下载文件
        
        Args:
            url: 下载链接
            filename: 保存的文件名
            save_path: 保存路径
            progress_callback: 进度回调函数
        
        Returns:
            下载结果字典
        """
        task_id = f"{filename}_{int(time.time())}"
        
        logger.info(f"开始下载文件: {filename}, URL: {url}")
        
        # 创建保存目录 - 使用Pathlib进行路径处理
        save_dir = Path(save_path).resolve()
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / filename
        
        # 确保文件名安全 - 移除路径分隔符
        safe_filename = Path(filename).name
        file_path = save_dir / safe_filename
        
        try:
            # 开始下载
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # 初始化任务信息
            self.download_tasks[task_id] = {
                'filename': safe_filename,
                'url': url,
                'total_size': total_size,
                'downloaded_size': 0,
                'status': 'downloading',
                'progress': 0,
                'speed': 0,
                'eta': 0
            }
            
            # 记录开始时间
            start_time = time.time()
            last_update_time = start_time
            
            # 写入文件
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 更新下载信息
                        current_time = time.time()
                        elapsed_time = current_time - start_time
                        
                        if elapsed_time > 0:
                            speed = downloaded_size / elapsed_time  # bytes per second
                            remaining_size = total_size - downloaded_size
                            eta = remaining_size / speed if speed > 0 else 0
                        else:
                            speed = 0
                            eta = 0
                        
                        progress = (downloaded_size / total_size * 100) if total_size > 0 else 0
                        
                        # 更新任务状态
                        self.download_tasks[task_id].update({
                            'downloaded_size': downloaded_size,
                            'progress': progress,
                            'speed': speed,
                            'eta': eta
                        })
                        
                        # 调用进度回调（每0.5秒更新一次，避免过于频繁）
                        if (current_time - last_update_time) >= 0.5 and progress_callback:
                            await progress_callback(task_id, self.download_tasks[task_id])
                            last_update_time = current_time
                        
                        # 允许其他异步任务运行
                        await asyncio.sleep(0)
            
            # 下载完成
            self.download_tasks[task_id]['status'] = 'completed'
            self.download_tasks[task_id]['progress'] = 100
            
            if progress_callback:
                await progress_callback(task_id, self.download_tasks[task_id])
            
            logger.success(f"文件下载完成: {filename}, 保存路径: {file_path}")
            
            return {
                'success': True,
                'task_id': task_id,
                'file_path': str(file_path),
                'message': f'文件 {filename} 下载完成'
            }
            
        except requests.exceptions.RequestException as e:
            self.download_tasks[task_id]['status'] = 'failed'
            self.download_tasks[task_id]['error'] = str(e)
            
            if progress_callback:
                await progress_callback(task_id, self.download_tasks[task_id])
            
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'message': f'下载失败: {str(e)}'
            }
        
        except Exception as e:
            self.download_tasks[task_id]['status'] = 'failed'
            self.download_tasks[task_id]['error'] = str(e)
            
            if progress_callback:
                await progress_callback(task_id, self.download_tasks[task_id])
            
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'message': f'下载失败: {str(e)}'
            }
    
    def get_task_info(self, task_id: str) -> dict:
        """获取下载任务信息"""
        return self.download_tasks.get(task_id, {})
    
    def get_all_tasks(self) -> dict:
        """获取所有下载任务"""
        return self.download_tasks.copy()
    
    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def format_speed(self, speed_bytes_per_sec: float) -> str:
        """格式化下载速度"""
        return f"{self.format_file_size(int(speed_bytes_per_sec))}/s"
    
    def format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}分{remaining_seconds}秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}时{minutes}分"
    
    def start_core(self, config_file_path: str, resources_path: str = "./resources") -> bool:
        """
        启动核心程序
        
        Args:
            config_file_path: 配置文件路径
            resources_path: 核心文件所在目录
            
        Returns:
            bool: 启动是否成功
        """
        try:
            if self.is_running:
                logger.warning("核心已经在运行中")
                return False
            
            # 获取核心文件路径
            core_filename = self.get_core_filename()
            core_path = Path(resources_path).resolve() / core_filename
            
            if not core_path.exists():
                logger.error(f"核心文件不存在: {core_path}")
                return False
            
            config_path = Path(config_file_path)
            if not config_path.exists():
                logger.error(f"配置文件不存在: {config_path}")
                return False
            
            # 创建子进程运行核心
            self.core_process = subprocess.Popen(
                [str(core_path), '', str(config_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.is_running = True
            
            # 启动输出读取线程
            output_thread = threading.Thread(target=self._read_output)
            output_thread.daemon = True
            output_thread.start()
            
            logger.success(f"核心启动成功: {core_filename}")
            return True
            
        except Exception as e:
            logger.error(f"启动核心失败: {str(e)}")
            self.is_running = False
            return False
    
    def stop_core(self) -> bool:
        """
        停止核心程序
        
        Returns:
            bool: 停止是否成功
        """
        try:
            if not self.is_running or not self.core_process:
                logger.warning("没有正在运行的核心进程")
                return False
            
            self.core_process.terminate()
            self.core_process.wait(timeout=5)
            self.is_running = False
            self.core_process = None
            
            logger.info("核心已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止核心失败: {str(e)}")
            return False
    
    def _read_output(self):
        """读取核心程序输出"""
        try:
            while self.is_running and self.core_process:
                line = self.core_process.stdout.readline()
                if line:
                    # 过滤ANSI转义序列（控制台颜色代码）
                    clean_line = self._filter_ansi_escape(line)
                    
                    # 识别日志等级
                    log_level = self._get_log_level(clean_line)
                    
                    # 调用所有日志回调函数，传递日志文本和等级
                    for callback in self.log_callbacks:
                        try:
                            # 使用异步方式执行UI更新，避免slot错误
                            if hasattr(callback, '__self__') and hasattr(callback.__self__, 'ui'):
                                # 如果是UI组件的方法，使用异步执行
                                import asyncio
                                asyncio.create_task(self._safe_callback(callback, clean_line, log_level))
                            else:
                                # 直接调用非UI回调
                                callback(clean_line, log_level)
                        except Exception as e:
                            logger.error(f"日志回调执行失败: {str(e)}")
                else:
                    break
        except Exception as e:
            logger.error(f"读取核心输出失败: {str(e)}")
        finally:
            self.is_running = False
    
    def _filter_ansi_escape(self, text: str) -> str:
        """
        过滤ANSI转义序列（控制台颜色代码）
        
        Args:
            text: 包含ANSI转义序列的文本
            
        Returns:
            str: 过滤后的干净文本
        """
        import re
        # 匹配常见的ANSI转义序列
        ansi_escape_patterns = [
            r'\x1b\[[0-9;]*m',  # 颜色代码
            r'\x1b\[[0-9;]*[A-HJ-ST]',  # 光标移动等控制代码
            r'\x1b\[[0-9;]*[f]',  # 光标定位
            r'\x1b\[[0-9;]*[K]',  # 清除行
        ]
        
        clean_text = text
        for pattern in ansi_escape_patterns:
            ansi_escape = re.compile(pattern)
            clean_text = ansi_escape.sub('', clean_text)
        
        return clean_text.strip()
    
    def _get_log_level(self, text: str) -> str:
        """
        识别日志等级
        
        Args:
            text: 日志文本
            
        Returns:
            str: 日志等级对应的CSS类名
        """
        import re
        
        # 检查日志中是否包含等级标识
        log_levels = ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'SUCCESS', 'FATA']
        for level in log_levels:
            # 使用正则表达式匹配日志等级（如 [ERROR], [WARNING] 等）
            pattern = r'\[(' + re.escape(level) + r')\]'
            if re.search(pattern, text, re.IGNORECASE):
                return level.lower()
        
        # 如果没有匹配到特定等级，检查常见的关键词
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ['error', 'failed', 'failure', 'exception', 'fatal']):
            return 'error'
        elif any(keyword in text_lower for keyword in ['warning', 'warn', 'caution']):
            return 'warning'
        elif any(keyword in text_lower for keyword in ['success', 'completed', 'finished', 'done', 'ready']):
            return 'success'
        elif any(keyword in text_lower for keyword in ['debug', 'trace']):
            return 'debug'
        
        # 默认使用info等级
        return 'info'
    
    async def _safe_callback(self, callback, line, log_level):
        """安全执行UI回调函数"""
        try:
            # 使用异步方式执行UI更新
            await callback(line, log_level)
        except Exception as e:
            logger.error(f"异步日志回调执行失败: {str(e)}")
    
    def add_log_callback(self, callback: Callable[[str], None]):
        """
        添加日志回调函数
        
        Args:
            callback: 日志回调函数，接收日志行作为参数
        """
        self.log_callbacks.append(callback)
    
    def remove_log_callback(self, callback: Callable[[str], None]):
        """
        移除日志回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.log_callbacks:
            self.log_callbacks.remove(callback)
    
    def clear_log_callbacks(self):
        """清除所有日志回调函数"""
        self.log_callbacks.clear()
    
    def get_core_status(self) -> dict:
        """
        获取核心状态信息
        
        Returns:
            dict: 核心状态信息
        """
        return {
            'is_running': self.is_running,
            'process_exists': self.core_process is not None,
            'log_callbacks_count': len(self.log_callbacks)
        }

# 创建全局核心管理器实例
core_manager = CoreManager()