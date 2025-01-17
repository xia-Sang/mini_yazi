from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.token import Token
from pygments.util import ClassNotFound
import curses
from pathlib import Path

class CursesHighlighter:
    """Curses语法高亮器"""
    
    def __init__(self):
        # 定义语法高亮的颜色映射
        self.color_map = {
            Token.Keyword: (curses.COLOR_BLUE, curses.COLOR_BLACK),
            Token.String: (curses.COLOR_GREEN, curses.COLOR_BLACK),
            Token.Number: (curses.COLOR_CYAN, curses.COLOR_BLACK),
            Token.Comment: (curses.COLOR_YELLOW, curses.COLOR_BLACK),
            Token.Operator: (curses.COLOR_MAGENTA, curses.COLOR_BLACK),
            Token.Name.Function: (curses.COLOR_RED, curses.COLOR_BLACK),
            Token.Name.Class: (curses.COLOR_GREEN, curses.COLOR_BLACK),
        }
        
    def init_colors(self, theme: str = "monokai"):
        """初始化curses颜色对，需要在curses初始化后调用"""
        for idx, (token, (fg, bg)) in enumerate(self.color_map.items(), start=10):
            curses.init_pair(idx, fg, bg)
            self.color_map[token] = idx
            
    def highlight_line(self, file_path: Path, line: str) -> list[tuple[str, int]]:
        """对单行文本进行语法高亮
        返回: [(文本片段, 颜色属性), ...]
        """
        try:
            lexer = get_lexer_for_filename(file_path.name)
        except ClassNotFound:
            lexer = TextLexer()
            
        tokens = list(lexer.get_tokens(line))
        result = []
        
        for token_type, value in tokens:
            # 查找最匹配的token类型
            while token_type not in self.color_map and token_type.parent:
                token_type = token_type.parent
                
            # 获取颜色属性
            color_pair = self.color_map.get(token_type, 0)
            attr = curses.color_pair(color_pair)
            
            result.append((value, attr))
            
        return result 