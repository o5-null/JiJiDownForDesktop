"""
主页UI模块
负责主页面的UI组件和功能
"""

import asyncio
from pathlib import Path
from nicegui import ui
from loguru import logger

from core_manager import CoreManager
from config_manager import config_manager
from system_info import system_info
from utils import create_file_browser_button
from core_status import update_core_status, get_core_status

# 创建全局实例
core_manager = CoreManager()


def create_home_page():
    """创建主页UI组件"""
    
    # 添加CSS样式定义
    ui.add_css("""
    .text-red { color: #f44336; font-weight: bold; }
    .text-orange { color: #ff9800; font-weight: bold; }
    .text-gray { color: #9e9e9e; }
    .text-green { color: #4caf50; font-weight: bold; }
    .text-blue { color: #2196f3; }
    .text-fata { color: #d32f2f; font-weight: bold; background-color: #ffebee; padding: 2px 4px; border-radius: 3px; }
    """)
    
    ui.label('唧唧2.0')
    ui.label('核心状态')
    
    # 显示系统信息
    sys_info = system_info.get_system_info()
    ui.label(f'系统: {sys_info["system"]} {sys_info["architecture"]} {sys_info["processor_type"]}')
    ui.label(f'机器类型: {sys_info["machine"]}')
    
    # 显示选择的核心文件
    core_filename = system_info.get_core_filename()
    core_status = ui.label(f'选择的核心文件: {core_filename}')
    
    # Hash校验结果显示
    hash_status = ui.label('').style('margin-top: 10px')
    
    # 核心运行状态显示
    core_running_status = ui.label('').style('margin-top: 10px; font-weight: bold')
    
    # 详细信息展开区域
    details_expansion = ui.expansion('详细信息', icon='info').style('margin-top: 10px')
    
    # 进度条和状态显示区域
    progress_container = ui.column().style('width: 100%; margin-top: 20px')
    
    # 更新核心运行状态显示
    def update_core_running_display():
        # 更新全局缓存变量core中的核心状态
        update_core_status()
        
        # 根据核心运行状态更新显示
        if get_core_status()['is_running']:
            core_running_status.set_text('核心状态: 正在运行')
            core_running_status.style('color: green')
        else:
            core_running_status.set_text('核心状态: 已停止')
            core_running_status.style('color: red')
    
    # 页面加载时初始化核心运行状态显示
    ui.timer(0.1, lambda: update_core_running_display(), once=True)
    
    # 定期更新核心运行状态显示（每5秒检查一次）
    ui.timer(5.0, lambda: update_core_running_display())
    
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
        
        # 添加刷新按钮
        async def refresh_status():
            ui.navigate.reload()
        
        ui.button('检查更新', on_click=refresh_status).style('margin-left: 10px')
    
    # 显示配置文件状态
    config_status_text = '✅ 配置文件已存在' if config_exists else '❌ 配置文件不存在'
    config_status_color = 'green' if config_exists else 'red'
    ui.label(config_status_text).style(f'color: {config_status_color}; margin-top: 10px')
    
    if not config_exists:
        ui.label('请先创建配置文件或前往设置页面进行配置').style('color: orange; margin-top: 5px')
    
    return {
        'update_core_running_display': update_core_running_display
    }