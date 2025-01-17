from typing import Optional, Union, Dict
from pathlib import Path
import chardet
import threading
from queue import Queue
import mmap

class FileViewer:
    """文件查看器核心类"""
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path).absolute()
        self.content: Optional[bytes] = None
        self.encoding: Optional[str] = None
        self.file_type: str = self._detect_file_type()
        self.cache: Dict[int, str] = {}  # 行缓存
        self.chunk_size = 4096  # 读取块大小
        self.load_queue = Queue()
        self.loading_thread: Optional[threading.Thread] = None
        
    def _detect_file_type(self) -> str:
        """检测文件类型"""
        if not self.file_path.exists():
            return 'not_exist'
        if self.file_path.is_dir():
            return 'directory'
        if self.file_path.is_symlink():
            return 'symlink'
        return 'file'
    
    def load(self) -> bool:
        """加载文件内容"""
        try:
            if self.file_type == 'not_exist':
                raise FileNotFoundError(f"文件不存在: {self.file_path}")
                
            if self.file_type == 'directory':
                return self._load_directory()
                
            # 读取文件内容
            with open(self.file_path, 'rb') as f:
                self.content = f.read()
                
            # 检测文件编码
            self.encoding = self._detect_encoding()
            
            # 如果是大文件，启动后台加载
            if len(self.content) > self.chunk_size * 2:
                self._start_background_load()
            else:
                # 小文件直接处理
                if self.encoding:
                    text = self.content.decode(self.encoding)
                    lines = text.splitlines()
                    for i, line in enumerate(lines):
                        self.cache[i] = line
                        
            return True
            
        except Exception as e:
            self.content = None
            self.encoding = None
            raise FileViewerError(f"加载文件失败: {str(e)}")
            
    def _start_background_load(self):
        """在后台线程中加载文件"""
        if self.loading_thread and self.loading_thread.is_alive():
            return
            
        self.loading_thread = threading.Thread(
            target=self._background_load,
            daemon=True
        )
        self.loading_thread.start()
        
    def _background_load(self):
        """后台加载文件内容"""
        try:
            with open(self.file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    # 先读取一小块用于编码检测
                    sample = mm[:min(self.chunk_size, len(mm))]
                    result = chardet.detect(sample)
                    self.encoding = result['encoding'] if result['confidence'] > 0.7 else 'utf-8'
                    
                    # 分块读取并解码
                    offset = 0
                    line_num = 0
                    buffer = []
                    
                    while offset < len(mm):
                        chunk = mm[offset:offset + self.chunk_size]
                        try:
                            text = chunk.decode(self.encoding)
                            lines = text.splitlines()
                            
                            # 处理跨块的行
                            if buffer:
                                lines[0] = buffer.pop() + lines[0]
                                
                            # 缓存完整的行
                            for line in lines[:-1]:
                                self.cache[line_num] = line
                                line_num += 1
                                
                            # 保存可能不完整的最后一行
                            buffer = [lines[-1]]
                            
                        except UnicodeDecodeError:
                            pass
                            
                        offset += self.chunk_size
                        
                    # 处理最后一行
                    if buffer:
                        self.cache[line_num] = buffer[0]
                        
        except Exception as e:
            self.load_queue.put(e)
            
    def get_line(self, line_num: int) -> Optional[str]:
        """获取指定行的内容"""
        return self.cache.get(line_num)
        
    def get_line_count(self) -> int:
        """获取总行数"""
        return max(self.cache.keys()) + 1 if self.cache else 0
    
    def _detect_encoding(self) -> Optional[str]:
        """检测文件编码"""
        if not self.content:
            return None
            
        try:
            result = chardet.detect(self.content)
            if result['confidence'] > 0.7:
                return result['encoding']
        except Exception:
            pass
            
        return None
    
    def _load_directory(self) -> bool:
        """加载目录内容"""
        try:
            entries = list(self.file_path.iterdir())
            self.content = "\n".join(str(entry.name) for entry in sorted(entries)).encode()
            self.encoding = 'utf-8'
            return True
        except Exception as e:
            raise FileViewerError(f"加载目录失败: {str(e)}")
    
    def get_content(self) -> Optional[str]:
        """获取文件内容"""
        if not self.content:
            return None
            
        # 如果已经缓存了行，从缓存构建内容
        if self.cache:
            lines = []
            for i in range(self.get_line_count()):
                line = self.cache.get(i)
                if line is not None:
                    lines.append(line)
            return '\n'.join(lines)
            
        # 否则尝试直接解码
        if self.encoding:
            try:
                return self.content.decode(self.encoding)
            except UnicodeDecodeError:
                pass
                
        # 如果是二进制文件，返回十六进制表示
        return self._format_hex_view()
    
    def _format_hex_view(self, bytes_per_line: int = 16) -> str:
        """格式化十六进制视图"""
        if not self.content:
            return ""
            
        lines = []
        for i in range(0, len(self.content), bytes_per_line):
            chunk = self.content[i:i + bytes_per_line]
            # 十六进制表示
            hex_line = " ".join(f"{b:02x}" for b in chunk)
            # ASCII 表示
            ascii_line = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            # 对齐处理
            hex_line = f"{hex_line:<{bytes_per_line * 3}}"
            lines.append(f"{i:08x}  {hex_line}  |{ascii_line}|")
            
        return "\n".join(lines)
    
    @property
    def file_info(self) -> dict:
        """获取文件基本信息"""
        return {
            'name': self.file_path.name,
            'path': str(self.file_path),
            'type': self.file_type,
            'size': self.file_path.stat().st_size if self.file_path.exists() else 0,
            'encoding': self.encoding
        }

class FileViewerError(Exception):
    """文件查看器异常"""
    pass 