"""
路由管理器模块
负责管理应用的路由和页面导航
"""

from nicegui import ui
from loguru import logger

from ui_home import create_home_page
from ui_settings import create_settings_page
from ui_log import create_log_page


class Router:
    """路由管理器类"""
    
    def __init__(self):
        self.current_route = '/'
        self.routes = {
            '/': {
                'name': '主页',
                'icon': 'home',
                'component': create_home_page,
                'description': '核心状态监控和文件管理'
            },
            '/log': {
                'name': '日志',
                'icon': 'list_alt',
                'component': create_log_page,
                'description': '核心运行日志查看'
            },
            '/settings': {
                'name': '设置',
                'icon': 'settings',
                'component': create_settings_page,
                'description': '应用配置和参数设置'
            }
        }
    
    def get_routes(self):
        """获取所有路由信息"""
        return self.routes
    
    def get_route_info(self, path):
        """获取指定路径的路由信息"""
        return self.routes.get(path, self.routes['/'])
    
    def navigate_to(self, path):
        """导航到指定路径"""
        if path in self.routes:
            self.current_route = path
            ui.navigate.to(path)
        else:
            logger.warning(f"未知的路由路径: {path}")
            self.current_route = '/'
            ui.navigate.to('/')
    
    def create_navigation_header(self):
        """创建导航头部"""
        with ui.header().classes('bg-blue-100 items-center justify-between px-4 py-2 shadow-md'):
            # 应用标题
            with ui.row().classes('items-center'):
                ui.icon('rocket', size='24px').classes('text-blue-600')
                ui.label('JiJiDown Desktop').classes('text-xl font-bold text-blue-800')
            
            # 导航菜单
            with ui.row().classes('items-center space-x-2'):
                for path, route_info in self.routes.items():
                    is_active = self.current_route == path
                    
                    ui.button(
                        route_info['name'],
                        icon=route_info['icon'],
                        on_click=lambda p=path: self.navigate_to(p)
                    ).props('flat').classes(
                        f"text-blue-700 hover:bg-blue-200 {'bg-blue-300' if is_active else ''}"
                    )
    
    def create_content_area(self):
        """创建内容区域"""
        with ui.column().classes('flex-grow p-4'):
            # 使用sub_pages实现客户端路由
            route_components = {path: route_info['component'] for path, route_info in self.routes.items()}
            ui.sub_pages(route_components).classes('w-full')
    
    def setup_spa_routes(self):
        """设置单页面应用路由"""
        
        @ui.page('/')
        @ui.page('/{_:path}')
        def main_spa():
            """主SPA页面"""
            # 创建导航头部
            self.create_navigation_header()
            
            # 创建内容区域
            self.create_content_area()
    
    def setup_legacy_routes(self):
        """设置传统路由（向后兼容）"""
        
        @ui.page('/legacy')
        def legacy_home():
            """传统主页路由"""
            create_home_page()
        
        @ui.page('/legacy/settings')
        def legacy_settings():
            """传统设置页面路由"""
            create_settings_page()
        
        @ui.page('/legacy/log')
        def legacy_log():
            """传统日志页面路由"""
            create_log_page()


# 创建全局路由管理器实例
router = Router()


def get_router():
    """获取路由管理器实例"""
    return router


def setup_routes():
    """设置所有路由"""
    router.setup_spa_routes()
    router.setup_legacy_routes()


if __name__ == "__main__":
    # 测试路由管理器
    print("路由管理器测试:")
    for path, info in router.get_routes().items():
        print(f"{path}: {info['name']} - {info['description']}")