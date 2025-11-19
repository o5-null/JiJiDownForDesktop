"""
日志管理器模块
负责日志的持久化存储和恢复
"""

import time
from pathlib import Path
from typing import List
from loguru import logger


class CoreLogManager:
    """日志管理器，负责日志的持久化存储和恢复"""
    
    def __init__(self, log_file_path: str = "logs/core_log.txt"):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_log_lines = 1000  # 最大保存日志行数
        
    def archive_logs(self) -> bool:
        """归档当前日志文件，将core_log.txt重命名为带时间戳的文件"""
        try:
            if not self.log_file_path.exists():
                logger.info("日志文件不存在，无需归档")
                return True
                
            # 获取文件大小
            file_size = self.log_file_path.stat().st_size
            
            # 如果文件为空或很小，无需归档
            if file_size == 0:
                logger.info("日志文件为空，无需归档")
                return True
                
            # 生成归档文件名（带时间戳和毫秒）
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            milliseconds = int(time.time() * 1000) % 1000
            archive_filename = f"{self.log_file_path.stem}_{timestamp}_{milliseconds:03d}.txt"
            archive_path = self.log_file_path.parent / archive_filename
            
            # 重命名文件进行归档
            self.log_file_path.rename(archive_path)
            logger.info(f"日志文件已归档: {archive_filename} (大小: {file_size} 字节)")
            
            # 创建新的空日志文件
            self.log_file_path.touch()
            
            # 清理旧的归档文件（保留最近7天的归档）
            self._cleanup_old_archives()
            
            return True
            
        except Exception as e:
            logger.error(f"日志归档失败: {str(e)}")
            return False
    
    def _cleanup_old_archives(self, retention_days: int = 7):
        """清理旧的归档文件，保留指定天数内的文件"""
        try:
            # 获取当前时间
            current_time = time.time()
            cutoff_time = current_time - (retention_days * 24 * 60 * 60)
            
            # 查找所有归档文件（基于当前日志文件名模式）
            archive_pattern = f"{self.log_file_path.stem}_*.txt"
            archive_files = list(self.log_file_path.parent.glob(archive_pattern))
            
            deleted_count = 0
            for archive_file in archive_files:
                # 跳过当前日志文件
                if archive_file.name == self.log_file_path.name:
                    continue
                    
                # 检查文件修改时间
                file_mtime = archive_file.stat().st_mtime
                
                if file_mtime < cutoff_time:
                    # 删除过期的归档文件
                    archive_file.unlink()
                    deleted_count += 1
                    logger.debug(f"删除过期归档文件: {archive_file.name}")
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个过期归档文件（保留最近 {retention_days} 天）")
                
        except Exception as e:
            logger.error(f"清理归档文件失败: {str(e)}")
    
    def save_log(self, log_line: str) -> bool:
        """保存单行日志到文件"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            formatted_line = f"[{timestamp}] {log_line}\n"
            
            # 追加写入日志文件
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(formatted_line)
            
            # 检查日志文件大小，如果超过限制则截断
            self._truncate_log_file()
            return True
            
        except Exception as e:
            logger.error(f"保存日志失败: {str(e)}")
            return False
    
    def load_logs(self) -> List[str]:
        """从文件加载所有日志"""
        try:
            if not self.log_file_path.exists():
                return []
            
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 返回最后max_log_lines行日志
            return [line.strip() for line in lines[-self.max_log_lines:]]
            
        except Exception as e:
            logger.error(f"加载日志失败: {str(e)}")
            return []
    
    def clear_logs(self) -> bool:
        """清空日志文件"""
        try:
            if self.log_file_path.exists():
                self.log_file_path.unlink()
            return True
            
        except Exception as e:
            logger.error(f"清空日志失败: {str(e)}")
            return False
    
    def _truncate_log_file(self):
        """截断日志文件，保持最大行数限制"""
        try:
            if not self.log_file_path.exists():
                return
            
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if len(lines) > self.max_log_lines:
                # 保留最后max_log_lines行
                truncated_lines = lines[-self.max_log_lines:]
                
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    f.writelines(truncated_lines)
                    
        except Exception as e:
            logger.error(f"截断日志文件失败: {str(e)}")


# 创建全局日志管理器实例
log_manager = CoreLogManager()