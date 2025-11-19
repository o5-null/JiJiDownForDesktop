"""
设置页面UI模块
负责设置页面的UI组件和功能
"""

from pathlib import Path
from nicegui import ui
from loguru import logger

from config_manager import config_manager
from utils import create_file_browser_button


def create_settings_page():
    """创建设置页面UI组件"""
    
    ui.label('设置').style('font-size: 24px; font-weight: bold; margin-bottom: 20px')

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
    
    return {
        'save_settings': save_settings,
        'reset_settings': reset_settings,
        'load_settings': load_settings
    }