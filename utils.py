import asyncio
from pathlib import Path
from nicegui import ui
import platform
from loguru import logger

class FileDialog:
    """文件对话框工具类"""
    
    @staticmethod
    async def select_directory(title="选择目录", start_dir=None):
        """选择目录对话框"""
        if start_dir is None:
            start_dir = Path.home()
        
        logger.debug(f"打开目录选择对话框: {title}, 起始目录: {start_dir}")
        
        # 由于NiceGUI没有原生的文件选择对话框，我们使用一个简单的输入框
        # 在实际应用中，可能需要使用tkinter或其他GUI库来实现完整的文件浏览功能
        
        result = {'path': ''}
        
        def close_dialog():
            dialog.close()
        
        def confirm_selection():
            result['path'] = path_input.value
            close_dialog()
            logger.info(f"用户选择了目录: {result['path']}")
        
        with ui.dialog() as dialog, ui.card():
            ui.label(title).style('font-size: 18px; font-weight: bold; margin-bottom: 10px')
            
            path_input = ui.input('路径', value=str(start_dir)).style('width: 400px')
            
            # 显示常用路径快捷方式
            with ui.row():
                ui.button('主目录', on_click=lambda: path_input.set_value(str(Path.home())))
                ui.button('桌面', on_click=lambda: path_input.set_value(str(Path.home() / 'Desktop')))
                if platform.system() == 'Windows':
                    ui.button('下载', on_click=lambda: path_input.set_value(str(Path.home() / 'Downloads')))
                else:
                    ui.button('下载', on_click=lambda: path_input.set_value(str(Path.home() / 'Downloads')))
            
            with ui.row().style('margin-top: 20px; justify-content: flex-end'):
                ui.button('取消', on_click=close_dialog)
                ui.button('确认', on_click=confirm_selection).style('background-color: #1976d2; color: white')
        
        dialog.open()
        await dialog
        
        logger.debug(f"目录选择对话框关闭，返回路径: {result['path']}")
        
        return result['path']
    
    @staticmethod
    async def select_file(title="选择文件", start_dir=None, file_filter=None):
        """选择文件对话框"""
        if start_dir is None:
            start_dir = Path.home()
        
        logger.debug(f"打开文件选择对话框: {title}, 起始目录: {start_dir}, 文件过滤器: {file_filter}")
        
        result = {'path': ''}
        
        def close_dialog():
            dialog.close()
        
        def confirm_selection():
            result['path'] = path_input.value
            close_dialog()
            logger.info(f"用户选择了文件: {result['path']}")
        
        with ui.dialog() as dialog, ui.card():
            ui.label(title).style('font-size: 18px; font-weight: bold; margin-bottom: 10px')
            
            path_input = ui.input('文件路径', value=str(start_dir)).style('width: 400px')
            
            # 显示常用路径快捷方式
            with ui.row():
                ui.button('主目录', on_click=lambda: path_input.set_value(str(Path.home())))
                ui.button('桌面', on_click=lambda: path_input.set_value(str(Path.home() / 'Desktop')))
                if platform.system() == 'Windows':
                    ui.button('下载', on_click=lambda: path_input.set_value(str(Path.home() / 'Downloads')))
            
            if file_filter:
                ui.label(f'支持的文件类型: {", ".join(file_filter)}').style('color: grey; font-size: 12px')
            
            with ui.row().style('margin-top: 20px; justify-content: flex-end'):
                ui.button('取消', on_click=close_dialog)
                ui.button('确认', on_click=confirm_selection).style('background-color: #1976d2; color: white')
        
        dialog.open()
        await dialog
        
        logger.debug(f"文件选择对话框关闭，返回路径: {result['path']}")
        
        return result['path']

def create_file_browser_button(input_field, dialog_title="选择路径", select_directory=True, file_filter=None):
    """创建文件浏览按钮"""
    async def browse_file():
        try:
            if select_directory:
                selected_path = await FileDialog.select_directory(dialog_title)
            else:
                selected_path = await FileDialog.select_file(dialog_title, file_filter=file_filter)
            
            if selected_path:
                input_field.value = selected_path
                ui.notify(f'已选择: {selected_path}', type='positive')
        except Exception as e:
            logger.error(f'选择文件时出错: {str(e)}')
            ui.notify(f'选择文件时出错: {str(e)}', type='negative')
    
    return browse_file