import json
from pathlib import Path
from nicegui import ui, app
import asyncio
from core_manager import core_manager
from utils import create_file_browser_button
from config_manager import config_manager
from system_info import system_info
from loguru import logger
import sys
import time
from typing import List, Optional

# 配置loguru日志
logger.remove()  # 移除默认的日志处理器
logger.add(sys.stderr,colorize=True, level="INFO")
logger.add("logs/JFD_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}", level="DEBUG")


# 创建默认文件夹
Path('./config').mkdir(parents=True, exist_ok=True)
Path('./TEMP').mkdir(parents=True, exist_ok=True)
Path('./Download').mkdir(parents=True, exist_ok=True)
Path('./logs').mkdir(parents=True, exist_ok=True)
Path('./resources').mkdir(parents=True, exist_ok=True)

# 软件启动时初始化配置
def initialize_config():
    """初始化配置文件，如果不存在则创建默认配置"""

    try:
        config_file_path = config_manager.get_config_file_path()
        
        # 只在主进程中记录配置文件已存在的信息，避免子进程重复日志
        if not config_file_path.exists():
            if __name__ == '__main__':
                logger.info(f"配置文件不存在，正在创建默认配置: {config_file_path}")
            # 加载默认配置（这会创建默认配置数据）
            config_manager.load_config()
            # 保存默认配置到文件
            if config_manager.save_config():
                if __name__ == '__main__':
                    logger.success(f"默认配置文件创建成功: {config_file_path}")
                return True
            else:
                if __name__ == '__main__':
                    logger.error(f"默认配置文件创建失败")
                return False
        else:
            # 只在主进程中记录配置文件已存在的信息
            if __name__ == '__main__':
                logger.info(f"配置文件已存在: {config_file_path}")
            # 加载现有配置
            config_manager.load_config()
            return True
            
    except Exception as e:
        if __name__ == '__main__':
            logger.error(f"配置文件初始化失败: {e}")
        return False

# 根据文档.md中的信息，支持不同架构的核心文件
def get_core_filename():
    """根据操作系统和架构返回对应的核心文件名 - 已废弃，请使用system_info.get_core_filename()"""
    return system_info.get_core_filename()

def get_system_info():
    """获取系统信息用于调试 - 已废弃，请使用system_info.get_system_info()"""
    return system_info.get_system_info()

# 创建全局缓存变量
core = {
    'exist': False,
    'filename': '',
    'path': '',
}

# 日志管理器类
class LogManager:
    """日志管理器，负责日志的持久化存储和恢复"""
    
    def __init__(self, log_file_path: str = "logs/session_log.txt"):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_log_lines = 1000  # 最大保存日志行数
    
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
log_manager = LogManager()

@ui.page('/')
def home():
    ui.label('唧唧2.0')
    ui.label('核心状态')
    
    # 显示系统信息
    sys_info = get_system_info()
    ui.label(f'系统: {sys_info["system"]} {sys_info["architecture"]} {sys_info["processor_type"]}')
    ui.label(f'机器类型: {sys_info["machine"]}')
    
    # 显示选择的核心文件
    core_filename = get_core_filename()
    core_status = ui.label(f'选择的核心文件: {core_filename}')
    
    # Hash校验结果显示
    hash_status = ui.label('').style('margin-top: 10px')
    
    # 详细信息展开区域
    details_expansion = ui.expansion('详细信息', icon='info').style('margin-top: 10px')
    
    # 进度条和状态显示区域
    progress_container = ui.column().style('width: 100%; margin-top: 20px')
    
    # 检查核心文件状态和hash校验
    hash_result = core_manager.check_core_hash()
    
    if not hash_result['exists']:
        # 文件不存在
        core_status.set_text(f'选择的核心文件: {core_filename} (未找到)')
        core_status.style('color: red')
        hash_status.set_text('状态: 核心文件不存在')
        hash_status.style('color: red')
        
        # 核心不存在时显示下载按键
        ui.label('核心文件未找到，请下载对应版本的核心文件').style('color: orange; margin-top: 10px')
        
        # 清空详细信息
        details_expansion.clear()
        
    elif hash_result['valid']:
        # Hash校验通过
        core_status.set_text(f'选择的核心文件: {core_filename} (已找到)')
        core_status.style('color: green')
        hash_status.set_text('状态: Hash校验通过，文件完整')
        hash_status.style('color: green')
        
        # 显示详细信息
        details_expansion.clear()
        with details_expansion:
            hash_source_text = '（备用）' if hash_result.get('hash_source') == 'backup' else ''
            ui.label(f'官方Hash{hash_source_text}: {hash_result["official_hash"]}').style('font-family: monospace; font-size: 12px')
            ui.label(f'本地Hash: {hash_result["local_hash"]}').style('font-family: monospace; font-size: 12px')
            ui.label('✅ 文件完整性验证通过').style('color: green')
        
    else:
        # Hash校验失败
        core_status.set_text(f'选择的核心文件: {core_filename} (已找到)')
        core_status.style('color: orange')
        hash_status.set_text(f'状态: {hash_result["message"]}')
        hash_status.style('color: orange')
        
        # Hash不匹配时显示更新按键
        ui.label('检测到文件需要更新').style('color: orange; margin-top: 10px')
        
        # 显示详细信息
        details_expansion.clear()
        with details_expansion:
            hash_source_text = '（备用）' if hash_result.get('hash_source') == 'backup' else ''
            ui.label(f'官方Hash{hash_source_text}: {hash_result.get("official_hash", "无法获取")}').style('font-family: monospace; font-size: 12px')
            ui.label(f'本地Hash: {hash_result.get("local_hash", "无法计算")}').style('font-family: monospace; font-size: 12px')
            ui.label('❌ 文件完整性验证失败').style('color: red')
    
    # 创建下载/更新按钮
    async def download_core():
            # 构建下载链接
            base_url = "https://jj.紫灵.top/PC/ReWPF/core/"
            download_url = base_url + core_filename
            
            # 清空进度容器
            progress_container.clear()
            
            # 创建进度条和状态标签
            with progress_container:
                ui.label(f'正在下载: {core_filename}').style('font-weight: bold; margin-bottom: 10px')
                
                # 进度条
                progress_bar = ui.linear_progress(value=0).style('width: 100%; margin-bottom: 10px')
                
                # 状态信息
                status_label = ui.label('准备下载...').style('margin-bottom: 5px')
                speed_label = ui.label('').style('color: blue')
                eta_label = ui.label('').style('color: green')
                
                # 下载完成提示
                completion_label = ui.label('').style('color: green; font-weight: bold; margin-top: 10px')
            
            # 进度回调函数
            async def update_progress(task_id, task_info):
                progress = task_info.get('progress', 0)
                status = task_info.get('status', 'unknown')
                downloaded_size = task_info.get('downloaded_size', 0)
                total_size = task_info.get('total_size', 0)
                speed = task_info.get('speed', 0)
                eta = task_info.get('eta', 0)
                
                # 更新进度条
                progress_bar.value = progress / 100
                
                # 更新状态信息
                if status == 'downloading':
                    status_label.set_text(f'进度: {progress:.1f}% ({core_manager.format_file_size(downloaded_size)} / {core_manager.format_file_size(total_size)})')
                    if speed > 0:
                        speed_label.set_text(f'速度: {core_manager.format_speed(speed)}')
                    if eta > 0:
                        eta_label.set_text(f'预计剩余时间: {core_manager.format_time(eta)}')
                elif status == 'completed':
                    status_label.set_text(f'下载完成: {core_manager.format_file_size(total_size)}')
                    speed_label.set_text('')
                    eta_label.set_text('')
                    completion_label.set_text('✅ 下载完成！文件已保存到 downloads 目录')
                    ui.notify('下载完成！', type='positive')
                elif status == 'failed':
                    error_msg = task_info.get('error', '未知错误')
                    status_label.set_text(f'下载失败: {error_msg}')
                    speed_label.set_text('')
                    eta_label.set_text('')
                    completion_label.set_text('❌ 下载失败，请重试').style('color: red')
                    ui.notify(f'下载失败: {error_msg}', type='negative')
            
            # 开始下载
            try:
                # 使用system_info获取默认路径
                download_path = Path(system_info.get_default_paths()['resources_dir'])
                
                result = await core_manager.download_file(
                    url=download_url,
                    filename=core_filename,
                    save_path=str(download_path),
                    progress_callback=update_progress
                )
                
                if result['success']:
                    # 下载成功，刷新页面状态
                    await asyncio.sleep(2)  # 等待2秒让用户看到完成信息
                    ui.navigate.reload()  # 刷新页面
                
            except Exception as e:
                completion_label.set_text(f'❌ 下载出错: {str(e)}').style('color: red')
                ui.notify(f'下载出错: {str(e)}', type='negative')
        
    # 检查配置文件和核心文件是否存在
    config_file_path = config_manager.get_config_file_path()
    config_exists = config_file_path.exists()
    
    # 根据文件状态显示不同的按钮
    with ui.row().style('margin-top: 10px'):
        button_text = '更新核心文件' if hash_result['exists'] else '下载核心文件'
        ui.button(button_text, on_click=download_core)
        
        # 当核心存在且配置文件存在时显示启动核心按钮
        if hash_result['exists'] and config_exists:
            # 添加日志页面按钮
            ui.button('查看日志', on_click=lambda: ui.navigate.to('/log')).style('margin-left: 10px')
        
        # 添加刷新按钮
        async def refresh_status():
            ui.navigate.reload()
        
        ui.button('检查更新', on_click=refresh_status).style('margin-left: 10px')
        
        # 添加设置页面按钮
        ui.button('设置', on_click=lambda: ui.navigate.to('/settings')).style('margin-left: 10px')
    
    # 显示配置文件状态
    config_status_text = '✅ 配置文件已存在' if config_exists else '❌ 配置文件不存在'
    config_status_color = 'green' if config_exists else 'red'
    ui.label(config_status_text).style(f'color: {config_status_color}; margin-top: 10px')
    
    if not config_exists:
        ui.label('请先创建配置文件或前往设置页面进行配置').style('color: orange; margin-top: 5px')

@ui.page('/settings')
def settings():
    ui.label('设置').style('font-size: 24px; font-weight: bold; margin-bottom: 20px')
    
    # 添加返回按钮
    with ui.row().style('margin-bottom: 20px'):

        def go_back():
            status = config_manager.save_config()
            ui.navigate.to('/')

        ui.button('← 返回主页', on_click=go_back).style('background-color: #f5f5f5; color: #333')

    # 加载当前配置
    current_config = config_manager.load_config()
    
    # 创建标签页来组织不同的设置类别
    with ui.tabs().classes('w-full') as tabs:
        ui.tab('基本设置', icon='settings')
        ui.tab('下载设置', icon='download')
        ui.tab('网络设置', icon='network_wifi')
        ui.tab('用户设置', icon='person')
        ui.tab('高级设置', icon='tune')
    
    with ui.tab_panels(tabs, value='基本设置').classes('w-full'):
        # 基本设置
        with ui.tab_panel('基本设置'):
            ui.label('日志设置').style('font-size: 18px; font-weight: bold; margin-top: 10px')
            
            # 日志级别
            log_level = ui.select(
                ['info', 'warning', 'error', 'debug', 'silent'],
                value=current_config.get('log-level', 'info'),
                label='日志级别'
            ).style('width: 200px')
            
            ui.label('外部控制器端口').style('font-size: 18px; font-weight: bold; margin-top: 20px')
            
            # 获取端口配置
            ports = config_manager.get_external_ports()
            
            # gRPC端口
            grpc_port = ui.number(
                label='gRPC端口',
                value=ports.get('grpc', 4000),
                min=1024,
                max=49151,
                validation={'端口号必须在1024-49151之间': lambda v: 1024 <= v <= 49151}
            ).style('width: 200px')
            
            # gRPC-Web端口
            grpc_web_port = ui.number(
                label='gRPC-Web端口',
                value=ports.get('grpc-web', 4100),
                min=1024,
                max=49151,
                validation={'端口号必须在1024-49151之间': lambda v: 1024 <= v <= 49151}
            ).style('width: 200px')
            
            # RESTful API端口
            restful_port = ui.number(
                label='RESTful API端口',
                value=ports.get('restful-api', 64001),
                min=1024,
                max=49151,
                validation={'端口号必须在1024-49151之间': lambda v: 1024 <= v <= 49151}
            ).style('width: 200px')
            
        # 下载设置
        with ui.tab_panel('下载设置'):
            ui.label('下载目录设置').style('font-size: 18px; font-weight: bold; margin-top: 10px')
            
            # 临时目录
            def validate_directory_path(value):
                if not value:  # 空值是允许的
                    return True
                from pathlib import Path
                path = Path(value)
                if path.exists() and path.is_dir():
                    return True
                return '目录不存在或不是有效目录'
            
            with ui.row().style('align-items: center; width: 100%'):
                temp_dir_input = ui.input(
                    label='临时目录',
                    placeholder='留空使用默认路径',
                    value=config_manager.get_temp_dir(),
                    validation={'目录路径无效': validate_directory_path}
                ).style('flex-grow: 1; margin-right: 10px')
                ui.button('浏览', on_click=create_file_browser_button(temp_dir_input, '选择临时目录')).style('margin-top: 20px')
            
            # 下载目录
            with ui.row().style('align-items: center; width: 100%'):
                download_dir_input = ui.input(
                    label='下载目录',
                    placeholder='留空使用默认路径',
                    value=config_manager.get_download_dir(),
                    validation={'目录路径无效': validate_directory_path}
                ).style('flex-grow: 1; margin-right: 10px')
                ui.button('浏览', on_click=create_file_browser_button(download_dir_input, '选择下载目录')).style('margin-top: 20px')
            
            # FFmpeg路径
            def validate_ffmpeg_path(value):
                if not value:  # 空值是允许的
                    return True
                from pathlib import Path
                path = Path(value)
                if path.exists() and path.is_file():
                    return True
                return '文件不存在或不是有效文件'
            
            with ui.row().style('align-items: center; width: 100%'):
                ffmpeg_path_input = ui.input(
                    label='FFmpeg路径',
                    placeholder='留空使用环境变量或默认版本',
                    value=config_manager.get_ffmpeg_path(),
                    validation={'文件路径无效': validate_ffmpeg_path}
                ).style('flex-grow: 1; margin-right: 10px')
                ui.button('浏览', on_click=create_file_browser_button(ffmpeg_path_input, '选择FFmpeg可执行文件', select_directory=False, file_filter=['exe', ''])).style('margin-top: 20px')
            
            ui.label('下载限制').style('font-size: 18px; font-weight: bold; margin-top: 20px')
            
            # 最大任务数
            max_tasks = ui.number(
                label='最大同时下载任务数',
                value=config_manager.get_max_task(),
                min=1,
                max=5,
                validation={'任务数必须在1-5之间': lambda v: 1 <= v <= 5}
            ).style('width: 200px')
            
            # 下载速度限制
            speed_limit = ui.number(
                label='下载速度限制 (MiB/s)',
                value=config_manager.get_download_speed_limit() // (1024 * 1024),
                min=0,
                max=1024,
                validation={'速度限制必须在0-1024 MiB/s之间': lambda v: 0 <= v <= 1024}
            ).style('width: 200px')
            
            # 禁用mCDN
            disable_mcdn = ui.checkbox(
                '禁用mCDN下载源',
                value=config_manager.get('download-task.disable-mcdn', False)
            )
            
        # 网络设置
        with ui.tab_panel('网络设置'):
            ui.label('代理设置').style('font-size: 18px; font-weight: bold; margin-top: 10px')
            
            # 代理地址
            def validate_proxy_url(value):
                if not value:  # 空值是允许的
                    return True
                # 简单的URL格式验证
                if value.startswith(('http://', 'https://', 'socks5://')):
                    return True
                return '代理地址格式不正确，应为 http://127.0.0.1:1080 或 socks5://127.0.0.1:1080'
            
            proxy_addr = ui.input(
                label='代理地址',
                placeholder='例如: http://127.0.0.1:1080',
                value=config_manager.get('jdm.proxy-addr', ''),
                validation={'代理地址格式不正确': validate_proxy_url}
            ).style('width: 300px')
            
            ui.label('下载设置').style('font-size: 18px; font-weight: bold; margin-top: 20px')
            
            # 最大重试次数
            max_retry = ui.number(
                label='最大重试次数',
                value=config_manager.get('jdm.max-retry', 3),
                min=1,
                max=10,
                validation={'重试次数必须在1-10之间': lambda v: 1 <= v <= 10}
            ).style('width: 200px')
            
            # 重试等待时间
            retry_wait = ui.number(
                label='重试等待时间 (秒)',
                value=config_manager.get('jdm.retry-wait', 5),
                min=1,
                max=600,
                validation={'等待时间必须在1-600秒之间': lambda v: 1 <= v <= 600}
            ).style('width: 200px')
            
            # 会话工作者数量
            session_workers = ui.number(
                label='会话工作者数量',
                value=config_manager.get('jdm.session-workers', 1),
                min=1,
                max=3,
                validation={'会话工作者数量必须在1-3之间': lambda v: 1 <= v < 3}
            ).style('width: 200px')
            
            # 分段工作者数量
            part_workers = ui.number(
                label='分段工作者数量',
                value=config_manager.get('jdm.part-workers', 4),
                min=1,
                max=8,
                validation={'分段工作者数量必须在1-8之间': lambda v: 1 <= v <= 8}
            ).style('width: 200px')
            
            # 最小分段大小
            min_split_size = ui.number(
                label='最小分段大小 (MiB)',
                value=config_manager.get('jdm.min-split-size', 1048576) // (1024 * 1024),
                min=1,
                max=100,
                validation={'分段大小必须在1-100 MiB之间': lambda v: 1 <= v <= 100}
            ).style('width: 200px')
            
            # 检查最快镜像
            check_best_mirror = ui.checkbox(
                '检查最快的下载源',
                value=config_manager.get('jdm.check-best-mirror', True)
            )
            
        # 用户设置
        with ui.tab_panel('用户设置'):
            ui.label('用户认证').style('font-size: 18px; font-weight: bold; margin-top: 10px')
            
            # 获取用户信息
            user_info = config_manager.get_user_info()
            
            # Access Token
            def validate_token_format(value):
                if not value:  # 空值是允许的
                    return True
                # 简单的Token格式验证 - 通常Token应该有一定长度
                if len(value) >= 10:  # 假设Token至少10个字符
                    return True
                return 'Token格式不正确，长度应该至少10个字符'
            
            access_token = ui.input(
                label='Access Token',
                password=True,
                placeholder='用于TV、APP接口登录',
                value=user_info.get('access-token', ''),
                validation={'Token格式不正确': validate_token_format}
            ).style('width: 400px')
            
            # Refresh Token
            refresh_token = ui.input(
                label='Refresh Token',
                password=True,
                placeholder='用于刷新Access Token',
                value=user_info.get('refresh-token', ''),
                validation={'Token格式不正确': validate_token_format}
            ).style('width: 400px')
            
            # Cookies
            cookies = ui.textarea(
                label='Cookies',
                placeholder='用于WEB接口登录',
                value=user_info.get('cookies', '')
            ).style('width: 400px; height: 100px')
            
            # Raw Access Token
            raw_access_token = ui.input(
                label='Raw Access Token',
                password=True,
                placeholder='手动设置Access Token（优先级更高）',
                value=user_info.get('raw-access-token', ''),
                validation={'Token格式不正确': validate_token_format}
            ).style('width: 400px')
            
            # Raw Cookies
            raw_cookies = ui.textarea(
                label='Raw Cookies',
                placeholder='手动设置Cookies（优先级更高）',
                value=user_info.get('raw-cookies', '')
            ).style('width: 400px; height: 100px')
            
            # 隐藏昵称
            hide_nickname = ui.checkbox(
                '隐藏用户信息（Premium用户专属）',
                value=user_info.get('hide-nickname', False)
            )
            
        # 高级设置
        with ui.tab_panel('高级设置'):
            ui.label('内存缓存').style('font-size: 18px; font-weight: bold; margin-top: 10px')
            
            # 内存缓存
            cache_in_ram = ui.checkbox(
                '启用内存缓存',
                value=config_manager.get('jdm.cache-in-ram', False)
            )
            
            # 内存缓存限制
            cache_in_ram_limit = ui.number(
                label='内存缓存限制 (MiB)',
                value=config_manager.get('jdm.cache-in-ram-limit', 512),
                min=500,
                max=16384,
                validation={'内存缓存限制必须在500-16384 MiB之间': lambda v: 500 <= v <= 16384}
            ).style('width: 200px')
            
            ui.label('安全设置').style('font-size: 18px; font-weight: bold; margin-top: 20px')
            
            # 跳过证书验证
            insecure_skip_verify = ui.checkbox(
                '跳过HTTPS证书验证',
                value=config_manager.get('jdm.insecure-skip-verify', False)
            )
            
            # 自定义根证书
            def validate_certificate_path(value):
                if not value:  # 空值是允许的
                    return True
                from pathlib import Path
                path = Path(value)
                if path.exists() and path.is_file():
                    # 检查文件扩展名
                    valid_extensions = ['.pem', '.crt', '.cer', '.der']
                    if path.suffix.lower() in valid_extensions:
                        return True
                    return '证书文件格式不正确，应为PEM、CRT、CER或DER格式'
                return '证书文件不存在'
            
            with ui.row().style('align-items: center; width: 100%'):
                custom_root_certificates = ui.input(
                    label='自定义根证书路径',
                    placeholder='PEM格式证书文件路径',
                    value=config_manager.get('jdm.custom-root-certificates', ''),
                    validation={'证书路径无效': validate_certificate_path}
                ).style('flex-grow: 1; margin-right: 10px')
                ui.button('浏览', on_click=create_file_browser_button(custom_root_certificates, '选择证书文件', select_directory=False, file_filter=['pem', 'crt', ''])).style('margin-top: 20px')
    
    # 底部按钮区域
    with ui.row().style('margin-top: 30px; justify-content: flex-end; width: 100%'):
        # 保存按钮
        async def save_settings():
            # 收集所有设置值
            settings_data = {
                'log-level': log_level.value,
                'external-controller-port': {
                    'grpc': int(grpc_port.value),
                    'grpc-web': int(grpc_web_port.value),
                    'restful-api': int(restful_port.value)
                },
                'download-task': {
                    'temp-dir': temp_dir_input.value,
                    'download-dir': download_dir_input.value,
                    'ffmpeg-path': ffmpeg_path_input.value,
                    'max-task': int(max_tasks.value),
                    'download-speed-limit': int(speed_limit.value) * 1024 * 1024,  # 转换为bytes
                    'disable-mcdn': disable_mcdn.value
                },
                'jdm': {
                    'max-retry': int(max_retry.value),
                    'retry-wait': int(retry_wait.value),
                    'session-workers': int(session_workers.value),
                    'part-workers': int(part_workers.value),
                    'min-split-size': int(min_split_size.value),
                    'proxy-addr': proxy_addr.value,
                    'check-best-mirror': check_best_mirror.value,
                    'cache-in-ram': cache_in_ram.value,
                    'cache-in-ram-limit': int(cache_in_ram_limit.value),
                    'insecure-skip-verify': insecure_skip_verify.value,
                    'custom-root-certificates': custom_root_certificates.value
                },
                'user-info': {
                    'access-token': access_token.value,
                    'refresh-token': refresh_token.value,
                    'cookies': cookies.value,
                    'raw-access-token': raw_access_token.value,
                    'raw-cookies': raw_cookies.value,
                    'hide-nickname': hide_nickname.value
                }
            }
            
            # 使用config_manager保存配置
            try:
                success = config_manager.save_config(settings_data)
                
                if success:
                    ui.notify('设置已保存！', type='positive')
                    # 显示保存的配置文件路径
                    config_path = config_manager.get_config_file_path()
                    ui.notify(f'配置文件路径: {config_path}', type='info', timeout=5000)
                else:
                    ui.notify('保存设置失败', type='negative')
                    
            except Exception as e:
                ui.notify(f'保存设置失败: {str(e)}', type='negative')
        
        # 重置按钮
        async def reset_settings():
            try:
                # 重置配置为默认值
                config_manager.reset_to_default()
                
                ui.notify('设置已重置为默认值！', type='positive')
                
                # 重新加载页面
                ui.navigate.reload()
                
            except Exception as e:
                ui.notify(f'重置设置失败: {str(e)}', type='negative')
        
        # 加载按钮
        async def load_settings():
            try:
                # 重新加载配置
                settings_data = config_manager.load_config()
                
                # 应用加载的设置
                if 'log-level' in settings_data:
                    log_level.value = settings_data['log-level']
                
                if 'external-controller-port' in settings_data:
                    ports = settings_data['external-controller-port']
                    grpc_port.value = ports.get('grpc', 4000)
                    grpc_web_port.value = ports.get('grpc-web', 4100)
                    restful_port.value = ports.get('restful-api', 64001)
                
                if 'download-task' in settings_data:
                    task = settings_data['download-task']
                    temp_dir_input.value = task.get('temp-dir', '')
                    download_dir_input.value = task.get('download-dir', '')
                    ffmpeg_path_input.value = task.get('ffmpeg-path', '')
                    max_tasks.value = task.get('max-task', 2)
                    speed_limit.value = task.get('download-speed-limit', 0) // (1024 * 1024)  # 转换回MiB
                    disable_mcdn.value = task.get('disable-mcdn', False)
                
                if 'jdm' in settings_data:
                    jdm = settings_data['jdm']
                    proxy_addr.value = jdm.get('proxy-addr', '')
                    max_retry.value = jdm.get('max-retry', 3)
                    retry_wait.value = jdm.get('retry-wait', 5)
                    session_workers.value = jdm.get('session-workers', 4)
                    part_workers.value = jdm.get('part-workers', 4)
                    min_split_size.value = jdm.get('min-split-size', 1048576) // (1024 * 1024)
                    check_best_mirror.value = jdm.get('check-best-mirror', True)
                    cache_in_ram.value = jdm.get('cache-in-ram', False)
                    cache_in_ram_limit.value = jdm.get('cache-in-ram-limit', 536870912) // (1024 * 1024)
                    insecure_skip_verify.value = jdm.get('insecure-skip-verify', False)
                    custom_root_certificates.value = jdm.get('custom-root-certificates', '')
                
                if 'user-info' in settings_data:
                    user = settings_data['user-info']
                    access_token.value = user.get('access-token', '')
                    refresh_token.value = user.get('refresh-token', '')
                    cookies.value = user.get('cookies', '')
                    raw_access_token.value = user.get('raw-access-token', '')
                    raw_cookies.value = user.get('raw-cookies', '')
                    hide_nickname.value = user.get('hide-nickname', False)
                
                ui.notify('设置已加载！', type='positive')
                    
            except Exception as e:
                ui.notify(f'加载设置失败: {str(e)}', type='negative')
        
        ui.button('重置为默认', on_click=reset_settings).style('margin-right: 10px')
        ui.button('保存设置', on_click=save_settings).style('background-color: #1976d2; color: white')

@ui.page('/log')
async def log_page():
    ui.label('核心运行日志').style('font-size: 24px; font-weight: bold; margin-bottom: 20px')
    
    # 添加返回按钮
    with ui.row().style('margin-bottom: 20px'):
        ui.button('← 返回主页', on_click=lambda: ui.navigate.to('/')).style('background-color: #f5f5f5; color: #333')
    
    # 显示核心文件信息
    core_filename = get_core_filename()
    config_file_path = config_manager.get_config_file_path()
    
    ui.label(f'核心文件: {core_filename}').style('font-size: 14px; margin-bottom: 5px')
    ui.label(f'配置文件: {config_file_path}').style('font-size: 14px; margin-bottom: 20px')
    
    # 使用ui.log()组件显示日志
    log_display = ui.log().style('width: 100%; height: 500px; font-family: monospace; font-size: 12px; overflow-y: auto; border: 1px solid #ccc; padding: 10px')

    
    # 控制按钮
    with ui.row().style('margin-top: 20px; margin-bottom: 20px'):
        # 开始运行按钮 - 根据核心运行状态动态禁用
        start_button = ui.button('开始运行', on_click=lambda: run_core(log_display, start_button, stop_button))
        
        # 停止运行按钮 - 根据核心运行状态动态禁用
        stop_button = ui.button('停止运行', on_click=lambda: stop_core(log_display, start_button, stop_button))
        
        ui.button('清空日志', on_click=lambda: clear_logs(log_display))
    
    # 核心运行状态显示
    status_label = ui.label('').style('font-size: 14px; margin-bottom: 10px; font-weight: bold')
    
    # 初始化按钮状态
    async def update_button_states():
        core_status = core_manager.get_core_status()
        is_running = core_status['is_running']
        
        # 更新按钮状态
        if start_button and stop_button:
            start_button.set_enabled(not is_running)
            stop_button.set_enabled(is_running)
        
        # 更新状态标签
        if status_label:
            if is_running:
                status_label.set_text('核心状态: 正在运行')
                status_label.style('color: green')
            else:
                status_label.set_text('核心状态: 已停止')
                status_label.style('color: red')
    
    # 页面加载时初始化按钮状态
    ui.timer(0.1, lambda: update_button_states(), once=True)
    
    # 定期更新按钮状态（每2秒检查一次）
    ui.timer(2.0, lambda: update_button_states())
    
    # 页面加载时恢复之前的日志
    async def load_previous_logs():
        try:
            previous_logs = log_manager.load_logs()
            if previous_logs:
                #log_display.push('=== 恢复之前的日志 ===')
                for log_line in previous_logs:
                    log_display.push(log_line)
                #log_display.push('=== 日志恢复完成 ===')
            else:
                log_display.push('日志页面已打开')
                log_display.push(f'核心文件: {core_filename}')
                log_display.push(f'配置文件: {config_file_path}')
                log_display.push('点击"开始运行"启动核心')
        except Exception as e:
            logger.error(f"加载历史日志失败: {str(e)}")
            log_display.push(f'加载历史日志失败: {str(e)}')
            log_display.push('日志页面已打开')
            log_display.push(f'核心文件: {core_filename}')
            log_display.push(f'配置文件: {config_file_path}')
            log_display.push('点击"开始运行"启动核心')
    
    # 页面加载完成后恢复日志
    ui.timer(0.1, lambda: load_previous_logs(), once=True)
    
    # 添加日志回调函数
    def log_callback(log_line):
        # 直接使用ui.log()推送日志，避免slot错误
        log_display.push(log_line.strip())
        # 同时保存到持久化存储
        log_manager.save_log(log_line.strip())
    
    # 清空日志的函数
    async def clear_logs(log_display):
        try:
            # 清空显示
            log_display.clear()
            # 清空持久化存储
            if log_manager.clear_logs():
                log_display.push('日志已清空')
                log_manager.save_log('用户手动清空日志')
            else:
                log_display.push('清空日志失败')
        except Exception as e:
            log_display.push(f'清空日志失败: {str(e)}')
    
    # 运行核心的函数
    async def run_core(log_display, start_button, stop_button):
        log_display.push('正在启动核心...')
        log_manager.save_log('正在启动核心...')
        
        # 禁用开始按钮，启用停止按钮
        if start_button and stop_button:
            start_button.set_enabled(False)
            stop_button.set_enabled(True)
        if status_label:
            status_label.set_text('核心状态: 正在启动...')
            status_label.style('color: orange')
        
        try:
            # 使用core_manager启动核心
            success = core_manager.start_core(str(config_file_path))
            
            if success:
                # 添加日志回调
                core_manager.add_log_callback(log_callback)
                log_display.push('核心启动成功！')
                log_manager.save_log('核心启动成功！')
                
                # 更新按钮状态和状态标签
                if start_button and stop_button:
                    start_button.set_enabled(False)
                    stop_button.set_enabled(True)
                if status_label:
                    status_label.set_text('核心状态: 正在运行')
                    status_label.style('color: green')
            else:
                log_display.push('核心启动失败')
                log_manager.save_log('核心启动失败')
                
                # 启动失败时恢复按钮状态
                if start_button and stop_button:
                    start_button.set_enabled(True)
                    stop_button.set_enabled(False)
                if status_label:
                    status_label.set_text('核心状态: 启动失败')
                    status_label.style('color: red')
            
        except Exception as e:
            log_display.push(f'启动核心失败: {str(e)}')
            log_manager.save_log(f'启动核心失败: {str(e)}')
            
            # 启动失败时恢复按钮状态
            if start_button and stop_button:
                start_button.set_enabled(True)
                stop_button.set_enabled(False)
            if status_label:
                status_label.set_text('核心状态: 启动失败')
                status_label.style('color: red')
    
    # 停止核心的函数
    async def stop_core(log_display, start_button, stop_button):
        # 禁用停止按钮，启用开始按钮
        if start_button and stop_button:
            start_button.set_enabled(False)
            stop_button.set_enabled(False)
        if status_label:
            status_label.set_text('核心状态: 正在停止...')
            status_label.style('color: orange')
        
        try:
            # 使用core_manager停止核心
            success = core_manager.stop_core()
            
            if success:
                # 移除日志回调
                core_manager.remove_log_callback(log_callback)
                log_display.push('核心已停止')
                log_manager.save_log('核心已停止')
                
                # 更新按钮状态和状态标签
                if start_button and stop_button:
                    start_button.set_enabled(True)
                    stop_button.set_enabled(False)
                if status_label:
                    status_label.set_text('核心状态: 已停止')
                    status_label.style('color: red')
            else:
                log_display.push('停止核心失败')
                log_manager.save_log('停止核心失败')
                
                # 停止失败时恢复按钮状态
                if start_button and stop_button:
                    start_button.set_enabled(False)
                    stop_button.set_enabled(True)
                if status_label:
                    status_label.set_text('核心状态: 停止失败')
                    status_label.style('color: orange')
            
        except Exception as e:
            log_display.push(f'停止核心失败: {str(e)}')
            log_manager.save_log(f'停止核心失败: {str(e)}')
            
            # 停止失败时恢复按钮状态
            if start_button and stop_button:
                start_button.set_enabled(False)
                stop_button.set_enabled(True)
            if status_label:
                status_label.set_text('核心状态: 停止失败')
                status_label.style('color: orange')

app.on_startup(initialize_config)
# 在UI启动前初始化配置
if __name__ in {"__main__", "__mp_main__"}:

    # 启动UI
    ui.run(root=home,title='JiJiDown Desktop', host='0.0.0.0', port=8080,native=True)