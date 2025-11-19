"""
日志页面UI模块
负责日志页面的UI组件和功能
"""

import asyncio
from nicegui import ui
from loguru import logger

from core_manager import CoreManager
from config_manager import config_manager
from system_info import system_info
from log_manager import log_manager
from core_status import update_core_status, get_core_status

# 创建全局实例
core_manager = CoreManager()


def create_log_page():
    """创建日志页面UI组件"""
    
    ui.label('核心运行日志').style('font-size: 24px; font-weight: bold; margin-bottom: 20px')
    
    # 显示核心文件信息
    core_filename = system_info.get_core_filename()
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
        # 更新全局缓存变量core中的核心状态
        update_core_status()
        
        # 使用全局缓存变量core中的状态信息
        is_running = get_core_status()['is_running']
        
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
    def log_callback(log_line, log_level):
        # 根据日志等级设置对应的CSS类名
        style_map = {
            'error': 'text-red',
            'warning': 'text-orange', 
            'success': 'text-green',
            'info': 'text-blue',
            'debug': 'text-gray',
            'fata': 'text-fata'  # FATA致命错误使用特殊样式
        }
        style = style_map.get(log_level, 'text-gray')
        
        # 使用classes参数推送带样式的日志
        log_display.push(log_line.strip(), classes=style)
        # 同时保存到持久化存储（保存原始文本）
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
                
                # 更新全局缓存变量core中的核心状态
                update_core_status()
                
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
                
                # 更新全局缓存变量core中的核心状态
                update_core_status()
                
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
                
                # 更新全局缓存变量core中的核心状态
                update_core_status()
                
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
                
                # 更新全局缓存变量core中的核心状态
                update_core_status()
                
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
    
    return {
        'update_button_states': update_button_states,
        'log_callback': log_callback,
        'run_core': run_core,
        'stop_core': stop_core,
        'clear_logs': clear_logs
    }