from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Tuple
import json
import curses

def default_color_schemes() -> Dict[str, Dict[str, Tuple[int, int]]]:
    """返回默认的颜色方案"""
    return {
        "default": {
            "directory": (curses.COLOR_BLUE, curses.COLOR_BLACK),
            "file": (curses.COLOR_GREEN, curses.COLOR_BLACK),
            "selected": (curses.COLOR_WHITE, curses.COLOR_BLUE),
            "title": (curses.COLOR_YELLOW, curses.COLOR_BLACK),
            "error": (curses.COLOR_RED, curses.COLOR_BLACK),
            "status": (curses.COLOR_CYAN, curses.COLOR_BLACK),
        },
        "dark": {
            "directory": (curses.COLOR_CYAN, curses.COLOR_BLACK),
            "file": (curses.COLOR_WHITE, curses.COLOR_BLACK),
            "selected": (curses.COLOR_BLACK, curses.COLOR_CYAN),
            "title": (curses.COLOR_YELLOW, curses.COLOR_BLACK),
            "error": (curses.COLOR_RED, curses.COLOR_BLACK),
            "status": (curses.COLOR_GREEN, curses.COLOR_BLACK),
        },
    }

@dataclass
class ViewerOptions:
    """查看器配置选项"""
    
    # 颜色主题
    theme: str = "default"  # 可选: default, dark, light, custom
    
    # 背景设置
    background_color: int = curses.COLOR_BLACK
    background_image: Optional[Path] = None
    background_opacity: float = 1.0  # 0.0-1.0
    
    # 字体设置
    font_size: int = 12
    font_family: str = "monospace"
    
    # 窗口设置
    default_width: int = 80
    default_height: int = 24
    min_width: int = 40
    min_height: int = 10
    
    # 布局设置
    sidebar_ratio: float = 0.3  # 侧边栏占比
    reading_sidebar_ratio: float = 0.15  # 阅读模式侧边栏占比
    
    # 颜色方案 - 使用 default_factory
    color_schemes: Dict[str, Dict[str, Tuple[int, int]]] = field(default_factory=default_color_schemes)
    
    # 语法高亮主题
    syntax_theme: str = "monokai"  # 可选: monokai, github, etc.
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'ViewerOptions':
        """从配置文件加载选项"""
        if config_path is None:
            config_path = Path.home() / ".config" / "yazi" / "config.json"
            
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return cls(**config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                
        return cls()  # 返回默认配置
        
    def save(self, config_path: Optional[Path] = None):
        """保存配置到文件"""
        if config_path is None:
            config_path = Path.home() / ".config" / "yazi" / "config.json"
            
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为可序列化的字典
        config = {
            "theme": self.theme,
            "background_color": self.background_color,
            "background_image": str(self.background_image) if self.background_image else None,
            "background_opacity": self.background_opacity,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "default_width": self.default_width,
            "default_height": self.default_height,
            "min_width": self.min_width,
            "min_height": self.min_height,
            "sidebar_ratio": self.sidebar_ratio,
            "reading_sidebar_ratio": self.reading_sidebar_ratio,
            "syntax_theme": self.syntax_theme,
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            
    def init_colors(self):
        """初始化颜色方案"""
        if not curses.has_colors():
            return
            
        curses.start_color()
        curses.use_default_colors()
        
        # 获取当前主题的颜色方案
        scheme = self.color_schemes.get(self.theme, self.color_schemes["default"])
        
        # 初始化颜色对
        for idx, (name, (fg, bg)) in enumerate(scheme.items(), start=1):
            curses.init_pair(idx, fg, bg)
            
    def get_color(self, name: str) -> int:
        """获取指定名称的颜色属性"""
        scheme = self.color_schemes.get(self.theme, self.color_schemes["default"])
        if name not in scheme:
            return 0
            
        idx = list(scheme.keys()).index(name) + 1
        return curses.color_pair(idx) 