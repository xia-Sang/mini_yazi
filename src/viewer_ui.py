import curses
import os
from pathlib import Path
from typing import List, Optional, Tuple
from .file_viewer import FileViewer, FileViewerError
from .preview_handler import PreviewHandler
from .syntax_highlighter import CursesHighlighter
from .options import ViewerOptions

class ViewerUI:
    def __init__(self, options: Optional[ViewerOptions] = None):
        self.options = options or ViewerOptions.load()
        self.screen = None
        self.current_path: Path = Path.cwd()
        self.entries: List[Path] = []
        self.current_index: int = 0
        self.viewer = FileViewer(self.current_path)
        self.left_win = None
        self.right_win = None
        self.preview_content: Optional[str] = None
        self.preview_handler = PreviewHandler()
        self.reading_mode = False  # 添加阅读模式标志
        self.scroll_position = 0   # 添加滚动位置
        self.highlighter = CursesHighlighter()
        
    def _init_curses(self):
        """初始化curses"""
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.start_color()
        curses.curs_set(0)
        
        # 初始化颜色方案
        self.options.init_colors()
        
        self.screen.keypad(True)
        
        # 初始化语法高亮颜色
        self.highlighter.init_colors()
        
        # 创建左右分屏窗口
        self._create_windows()
        
    def _cleanup_curses(self):
        """清理curses设置"""
        if self.screen:
            curses.curs_set(1)  # 恢复光标
            self.screen.keypad(False)
            curses.echo()
            curses.nocbreak()
            curses.endwin()
            
    def _create_windows(self):
        """创建左右分屏窗口"""
        height, width = self.screen.getmaxyx()
        # 正常模式下的左右分屏
        self.normal_left_width = width // 2
        # 阅读模式下的左右分屏
        self.reading_left_width = width // 6  # 阅读模式时左窗口更窄
        
        self._resize_windows(self.normal_left_width)
        
    def _resize_windows(self, left_width: int):
        """调整窗口大小"""
        height, width = self.screen.getmaxyx()
        
        # 重新创建左右窗口
        self.left_win = curses.newwin(height, left_width, 0, 0)
        self.left_win.keypad(True)
        self.right_win = curses.newwin(height, width - left_width, 0, left_width)
        
    def _display_preview(self):
        """显示预览内容"""
        if not self.entries or self.current_index >= len(self.entries):
            return
            
        height, width = self.right_win.getmaxyx()
        self.right_win.erase()
        
        # 获取当前选中的文件
        selected = self.entries[self.current_index]
        
        # 显示预览窗口标题
        title = f"预览: {selected.name}"
        self.right_win.addstr(0, 0, title, curses.color_pair(3) | curses.A_BOLD)
        self.right_win.addstr(1, 0, "-" * (width - 1))
        
        try:
            # 如果是目录，显示目录信息
            if selected.is_dir():
                self._preview_directory(selected, height, width)
            else:
                self._preview_file(selected, height, width)
                
        except Exception as e:
            self.right_win.addstr(2, 0, f"预览失败: {str(e)}")
            
        self.right_win.noutrefresh()
        
    def _preview_directory(self, path: Path, height: int, width: int):
        """预览目录内容"""
        try:
            entries = sorted(list(path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            self.right_win.addstr(2, 0, f"包含 {len(entries)} 个项目")
            
            for i, entry in enumerate(entries[:height-4]):
                prefix = "📁 " if entry.is_dir() else "📄 "
                name = entry.name
                if len(name) > width - 5:
                    name = name[:width-8] + "..."
                self.right_win.addstr(i+3, 0, f"{prefix}{name}")
                
        except Exception as e:
            self.right_win.addstr(2, 0, f"无法读取目录: {str(e)}")
            
    def _preview_file(self, path: Path, height: int, width: int):
        """预览文件内容"""
        try:
            file_type, content = self.preview_handler.get_preview(path)
            
            # 显示文件类型
            self.right_win.addstr(2, 0, f"类型: {file_type}")
            
            # 显示预览内容
            lines = content.split('\n')
            for i, line in enumerate(lines[:height-4]):
                if len(line) > width - 2:
                    line = line[:width-5] + "..."
                self.right_win.addstr(i+3, 0, line)
                
        except Exception as e:
            self.right_win.addstr(2, 0, f"无法预览文件: {str(e)}")
            
    def _display_entries(self):
        """显示文件列表"""
        height, width = self.left_win.getmaxyx()
        self.left_win.erase()
        
        # 显示当前路径
        self.left_win.addstr(0, 0, f"当前路径: {self.current_path}", curses.A_BOLD)
        self.left_win.addstr(1, 0, "-" * (width - 1))
        
        # 显示文件列表
        visible_entries = height - 4
        start_index = max(0, min(self.current_index - visible_entries // 2,
                               len(self.entries) - visible_entries))
        
        for i in range(visible_entries):
            idx = start_index + i
            if idx >= len(self.entries):
                break
                
            entry = self.entries[idx]
            name = ".." if entry == self.current_path.parent else entry.name
            
            attr = curses.A_NORMAL
            if idx == self.current_index:
                attr |= curses.A_REVERSE
            if entry.is_dir():
                attr |= curses.color_pair(1)
            else:
                attr |= curses.color_pair(2)
                
            if len(name) > width - 3:
                name = name[:width-6] + "..."
                
            self.left_win.addstr(i + 2, 0, f" {name:<{width-2}}", attr)
            
        # 显示帮助信息
        status_line = "↑↓: 移动  ←→: 导航  Enter: 打开  q: 退出"
        self.left_win.addstr(height-1, 0, status_line[:width-1], curses.A_BOLD)
        
        self.left_win.noutrefresh()
        self._display_preview()  # 更新预览窗口
        curses.doupdate()
        
    def _load_current_directory(self):
        """加载当前目录内容"""
        try:
            self.entries = sorted(
                list(self.current_path.iterdir()),
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
            if self.current_path.parent != self.current_path:  # 不是根目录
                self.entries.insert(0, self.current_path.parent)  # 添加 ..
            self.current_index = 0
        except Exception as e:
            raise FileViewerError(f"无法加载目录 {self.current_path}: {str(e)}")
            
    def _handle_input(self) -> bool:
        """处理用户输入"""
        key = self.left_win.getch()  # 从左窗口获取输入
        
        if key in [ord('q'), ord('Q')]:
            return False
            
        elif key == curses.KEY_UP:
            if self.current_index > 0:
                self.current_index -= 1
            
        elif key == curses.KEY_DOWN:
            if self.current_index < len(self.entries) - 1:
                self.current_index += 1
            
        elif key in [curses.KEY_RIGHT, ord('\n')]:
            selected = self.entries[self.current_index]
            if selected.is_dir():
                self.current_path = selected
                self._load_current_directory()
            else:
                self._view_file(selected)
                
        elif key == curses.KEY_LEFT:
            if self.current_path.parent != self.current_path:
                self.current_path = self.current_path.parent
                self._load_current_directory()
                
        return True
        
    def _display_reading_sidebar(self, file_path: Path):
        """显示阅读模式下的左侧边栏"""
        height, width = self.left_win.getmaxyx()
        self.left_win.erase()
        
        try:
            # 显示返回提示
            self.left_win.addstr(0, 0, "返回上级:", curses.A_BOLD)
            self.left_win.addstr(1, 0, "-" * (width - 1))
            
            # 获取父目录路径
            parent_dir = file_path.parent
            try:
                # 尝试获取相对路径
                rel_path = parent_dir.relative_to(Path.cwd())
                if str(rel_path) == '.':
                    display_path = '.'
                else:
                    display_path = str(rel_path)
            except ValueError:
                # 如果无法获取相对路径，使用绝对路径
                display_path = str(parent_dir)
            
            # 处理显示长度
            if len(display_path) > width - 4:
                display_path = "..." + display_path[-(width-7):]
            
            # 显示路径
            self.left_win.addstr(2, 1, display_path, curses.color_pair(1))
            
        except curses.error:
            pass
            
        self.left_win.refresh()

    def _view_file(self, file_path: Path):
        """查看文件内容"""
        try:
            # 创建新的文件查看器实例
            self.viewer = FileViewer(file_path)
            self.viewer.load()
            
            # 获取内容并预处理
            content = self.viewer.get_content()
            if not content:
                return
                
            # 进入阅读模式
            self.reading_mode = True
            self.scroll_position = 0
            
            # 调整窗口大小
            self._resize_windows(self.reading_left_width)
            
            # 预先计算一些常量
            height, _ = self.right_win.getmaxyx()
            visible_lines = height - 4
            
            # 显示初始内容
            self._display_reading_sidebar(file_path)
            self._display_file_content(file_path)
            
            # 主循环
            while True:
                ch = self.screen.getch()
                
                # 快速退出检查
                if ch in [27, ord('q')]:  # ESC 或 q
                    break
                    
                # 计算最大滚动位置
                total_lines = self.viewer.get_line_count()
                max_scroll = max(0, total_lines - visible_lines)
                
                # 处理导航
                if ch == curses.KEY_UP:
                    if self.scroll_position > 0:
                        self.scroll_position -= 1
                        self._display_file_content(file_path)
                elif ch == curses.KEY_DOWN:
                    if self.scroll_position < max_scroll:
                        self.scroll_position += 1
                        self._display_file_content(file_path)
                elif ch == curses.KEY_PPAGE:  # Page Up
                    self.scroll_position = max(0, self.scroll_position - visible_lines)
                    self._display_file_content(file_path)
                elif ch == curses.KEY_NPAGE:  # Page Down
                    self.scroll_position = min(max_scroll, self.scroll_position + visible_lines)
                    self._display_file_content(file_path)
                elif ch == ord('g'):  # 跳到开头
                    self.scroll_position = 0
                    self._display_file_content(file_path)
                elif ch == ord('G'):  # 跳到结尾
                    self.scroll_position = max_scroll
                    self._display_file_content(file_path)
                    
            # 恢复正常模式
            self.reading_mode = False
            self._resize_windows(self.normal_left_width)
            
            # 重新加载当前目录
            self.viewer = FileViewer(self.current_path)
            self._load_current_directory()
            self._display_entries()
            
        except FileViewerError as e:
            self._show_error(str(e))
            
    def _display_file_content(self, file_path: Path):
        """显示文件内容"""
        height, width = self.right_win.getmaxyx()
        self.right_win.erase()
        
        try:
            # 显示文件标题
            title = f"文件: {file_path.name}"
            if len(title) > width - 2:
                title = title[:width-5] + "..."
            self.right_win.addstr(0, 0, title[:width-1], curses.color_pair(3) | curses.A_BOLD)
            self.right_win.addstr(1, 0, "-" * min(width - 1, 80))
            
            # 计算可显示的行范围
            visible_lines = height - 4
            total_lines = self.viewer.get_line_count()
            
            # 显示内容
            for i in range(visible_lines):
                line_num = self.scroll_position + i
                if line_num >= total_lines:
                    break
                    
                try:
                    # 获取当前行内容
                    line = self.viewer.get_line(line_num)
                    if line is None:
                        continue
                        
                    # 显示行号
                    line_num_str = f"{line_num+1:4} "
                    self.right_win.addstr(i + 2, 0, line_num_str, curses.A_DIM)
                    
                    # 获取高亮内容并显示
                    highlighted = self.highlighter.highlight_line(file_path, line)
                    current_x = 5
                    
                    for text, attr in highlighted:
                        if current_x >= width:
                            break
                        try:
                            self.right_win.addstr(i + 2, current_x, text, attr)
                            current_x += len(text)
                        except curses.error:
                            break
                            
                except curses.error:
                    continue
                    
            # 显示加载状态
            if self.viewer.loading_thread and self.viewer.loading_thread.is_alive():
                status = "正在加载..."
            else:
                status = f"第 {self.scroll_position + 1}-{min(self.scroll_position + visible_lines, total_lines)} 行，共 {total_lines} 行"
                
            controls = "↑↓: 滚动  PgUp/PgDn: 翻页  g/G: 开头/结尾  ESC/q: 返回"
            status_line = f"{status} | {controls}"
            
            if len(status_line) > width - 2:
                status_line = status_line[:width-5] + "..."
            self.right_win.addstr(height-1, 0, status_line.center(width-1), curses.A_BOLD)
            
        except curses.error:
            pass
            
        self.right_win.refresh()
        
    def _show_error(self, message: str):
        """显示错误信息"""
        height, width = self.right_win.getmaxyx()
        self.right_win.addstr(height-1, 0, f"错误: {message}", curses.A_BOLD | curses.A_REVERSE)
        self.right_win.getch()
        
    def run(self):
        """运行查看器"""
        try:
            self._init_curses()
            self._load_current_directory()
            
            while True:
                self._display_entries()
                if not self._handle_input():
                    break
                    
        except Exception as e:
            if hasattr(self, '_cleanup_curses'):
                self._cleanup_curses()
            print(f"发生错误: {str(e)}")
        finally:
            if hasattr(self, '_cleanup_curses'):
                self._cleanup_curses() 