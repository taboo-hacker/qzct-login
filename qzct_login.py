import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication

# 确保日志系统在程序启动时就被初始化
from config import load_config

# 加载配置
load_config()

# 导入主窗口
from main_window import MainWindow


def set_autostart(enable=True):
    """
    设置应用程序在Windows系统中开机自启动
    
    使用Windows任务计划程序(SchTasks)创建自启动任务，以SYSTEM权限运行。
    这样即使没有用户登录，程序也能在系统启动时自动执行。
    
    Args:
        enable (bool): True表示启用自启动，False表示禁用自启动
    
    Returns:
        bool: 操作是否成功
    
    工作流程:
        1. 检查是否具有管理员权限
        2. 如果没有管理员权限，请求以管理员身份重新运行
        3. 使用schtasks命令创建/删除自启动任务
        4. 任务名称为"QZCT Login"，在系统启动时以最高权限运行
    """
    app_name = "QZCT Login"
    app_path = os.path.abspath(sys.argv[0])
    
    import ctypes
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    
    if enable:
        # 系统启动时运行的命令，使用--background参数确保不显示主窗口
        run_cmd = f'"{app_path}" --background'
        cmd = [
            "schtasks", "/create", "/tn", app_name, "/tr", 
            run_cmd, "/sc", "onstart", "/rl", "highest", 
            "/ru", "SYSTEM", "/f"
        ]
        
        if not is_admin:
            # 以管理员身份重新运行，使用--set-autostart参数，不显示主窗口
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, 
                f'"{app_path}" --set-autostart={1} --background', None, 1
            )
            # 对于非管理员权限请求，返回True表示已触发权限请求，实际结果由重新运行的进程处理
            return True
        else:
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True
            except subprocess.CalledProcessError as e:
                return False
    else:
        cmd = ["schtasks", "/delete", "/tn", app_name, "/f"]
        
        if not is_admin:
            # 以管理员身份重新运行，使用--set-autostart参数，不显示主窗口
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, 
                f'"{app_path}" --set-autostart={0} --background', None, 1
            )
            # 对于非管理员权限请求，返回True表示已触发权限请求，实际结果由重新运行的进程处理
            return True
        else:
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True
            except subprocess.CalledProcessError as e:
                return False


def check_autostart():
    """
    检查应用程序是否已设置开机自启动
    
    通过查询Windows任务计划程序来确认自启动任务是否存在。
    
    Returns:
        bool: True表示自启动任务已存在，False表示不存在
    
    使用方法:
        is_enabled = check_autostart()
        if is_enabled:
            print("程序已设置开机自启动")
    """
    app_name = "QZCT Login"
    cmd = ["schtasks", "/query", "/tn", app_name, "/fo", "list"]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """
    程序入口函数
    
    处理命令行参数并启动主窗口。
    
    命令行参数说明:
        --set-autostart=1 : 启用开机自启动
        --set-autostart=0 : 禁用开机自启动
        --set-autostart   : 旧版参数，启用开机自启动
        --background      : 后台运行模式，不显示主窗口
    
    程序启动流程:
        1. 解析命令行参数，检查是否有自启动设置请求
        2. 如果有自启动请求，执行相应的设置操作后退出
        3. 否则检查是否为后台运行模式
        4. 后台模式：执行任务后退出
        5. 正常模式：创建QApplication实例并显示主窗口
        6. 进入Qt事件循环，等待用户操作
    
    Returns:
        int: 程序退出码（通常为0表示正常退出）
    """
    autostart_arg = None
    for arg in sys.argv:
        if arg.startswith("--set-autostart="):
            autostart_arg = arg.split("=")[1]
            break
    
    if autostart_arg is not None:
        from config import global_config, save_config
        enable = autostart_arg == "1"
        global_config["AUTOSTART"] = enable
        save_config()
        set_autostart(enable=enable)
        return
    
    if "--set-autostart" in sys.argv:
        from config import global_config, save_config
        global_config["AUTOSTART"] = True
        save_config()
        set_autostart(enable=True)
        return
    
    # 检查是否为后台运行模式
    is_background = "--background" in sys.argv
    
    if is_background:
        # 后台模式：直接执行任务，不显示主窗口
        # 初始化日志系统，确保后台模式也能正确记录日志
        from logger import Logger, init_logger
        init_logger(gui_log_widget=None, level=1)  # INFO级别
        
        from tasks import run_tasks_once
        run_tasks_once()
        return
    
    # 正常模式：显示主窗口
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()