import sys
import sqlite3
import threading
from typing import Optional, Dict, List
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import platform
import logging
import os
import webbrowser
import tempfile
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image, ImageTk
import io
import time

# 配置日志
logging.basicConfig(level=logging.WARNING, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   datefmt='%H:%M:%S')

# 配置matplotlib样式和中文字体支持
plt.style.use('seaborn-darkgrid')
if platform.system() == 'Windows':
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 微软雅黑
elif platform.system() == 'Darwin':
    plt.rcParams['font.sans-serif'] = ['PingFang HK']  # macOS 的苹方字体
else:
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']  # Linux 的文泉驿微米黑
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class TreeFrame(ttk.Frame):
    """文件树显示框架
    
    负责显示SQLite数据库中的文件树结构，支持异步加载和展开/折叠操作。
    """
    
    def __init__(self, master, **kwargs):
        """初始化TreeFrame
        
        Args:
            master: 父级窗口
            **kwargs: 传递给父类的参数
        """
        super().__init__(master, **kwargs)
        
        # 保存对主窗口的引用
        self.app = master
        
        # 配置样式
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        
        # 创建并配置Treeview组件
        self.tree = ttk.Treeview(
            self,
            columns=('size', 'isdir'),
            show='tree headings'
        )
        self.tree.heading('size', text='Size')
        self.tree.column('size', width=100)
        self.tree.column('isdir', width=0, stretch=False)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局组件
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # 初始化成员变量
        self.db_path = None
        self._load_lock = threading.Lock()
        self._loaded_nodes = set()
        self.root_node = None
        
        # 绑定事件
        self.tree.bind('<<TreeviewOpen>>', self._on_item_opened)
        
        logging.debug("TreeFrame initialized")
    
    def set_database(self, db_path: str):
        """设置要显示的数据库文件
        
        Args:
            db_path: 数据库文件的路径
        """
        logging.debug(f"Setting database: {db_path}")
        self.db_path = db_path
        self._loaded_nodes.clear()
        self.clear_tree()
        
        # 创建根节点
        self._create_root_node()
        self.load_root()
    
    def clear_tree(self):
        """清空树形视图中的所有项目"""
        logging.debug("Clearing tree")
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def _create_root_node(self):
        """创建根节点并计算总大小"""
        if not self.db_path:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 计算所有文件的总大小
            cursor.execute("SELECT SUM(file_size) FROM cache_file WHERE isdir = 0")
            total_size = cursor.fetchone()[0] or 0
            
            # 计算文件和文件夹的数量
            cursor.execute("SELECT COUNT(*) FROM cache_file WHERE isdir = 0")
            file_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cache_file WHERE isdir = 1")
            dir_count = cursor.fetchone()[0]
            
            # 获取数据库文件名
            db_name = os.path.basename(self.db_path)
            
            # 创建根节点
            root_text = f"{db_name} ({dir_count}个文件夹, {file_count}个文件)"
            self.root_node = self.tree.insert('', 'end', text=root_text, values=(self._format_size(total_size),))
            self.tree.set(self.root_node, 'isdir', True)
            
            conn.close()
            logging.debug(f"Created root node: {root_text}")
            
        except sqlite3.Error as e:
            logging.error(f"Database error while creating root node: {e}")
        except Exception as e:
            logging.error(f"Error creating root node: {e}")
    
    def load_root(self):
        """加载根目录的内容"""
        logging.debug("Loading root directory")
        if not self.db_path or not self.root_node:
            logging.warning("No database path or root node")
            return
        threading.Thread(target=self._load_items, args=('/', self.root_node)).start()
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小显示
        
        Args:
            size: 文件大小（字节）
            
        Returns:
            str: 格式化后的大小字符串（B/KB/MB/GB）
        """
        if size == 0:
            return ""
        
        units = [
            (1024 * 1024 * 1024, 'GB'),
            (1024 * 1024, 'MB'),
            (1024, 'KB'),
            (1, 'B')
        ]
        
        for divisor, unit in units:
            if size >= divisor:
                value = size / divisor
                if unit == 'B':
                    return f"{int(value)} {unit}"
                return f"{value:.2f} {unit}"
        
        return f"{size} B"
    
    def _load_items(self, parent_path: str, parent_item: str = ''):
        """加载指定路径下的所有项目
        
        Args:
            parent_path: 父级路径
            parent_item: 父级项目的ID
        """
        logging.debug(f"Loading items for path: {parent_path}, parent_item: {parent_item}")
        if not self.db_path:
            logging.warning("No database path set")
            return
            
        with self._load_lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = """
                SELECT id, server_filename, file_size, isdir
                FROM cache_file
                WHERE parent_path = ?
                ORDER BY isdir DESC, server_filename
                """
                
                # 记录实际执行的SQL语句
                params = (parent_path,)
                logging.debug(f"Executing SQL: {query} with params: {params}")
                
                cursor.execute(query, params)
                items = cursor.fetchall()
                logging.debug(f"Found {len(items)} items in {parent_path}")
                
                # 存储需要计算大小的文件夹
                folders_to_calculate = []
                
                for item in items:
                    _, name, size, isdir = item
                    logging.debug(f"Processing item: {name} (size={size}, isdir={isdir})")
                    
                    if isdir:
                        # 对于文件夹，先显示"计算中..."
                        size_str = "计算中..."
                        folders_to_calculate.append((name, parent_item))
                    else:
                        # 对于文件，直接显示大小
                        size_str = self._format_size(size)
                    
                    self.after(0, self._insert_item, parent_item, name, size_str, isdir)
                
                # 启动新线程计算所有文件夹的大小
                if folders_to_calculate:
                    threading.Thread(target=self._calculate_folders_size, 
                                  args=(folders_to_calculate, parent_path)).start()
                
            except sqlite3.Error as e:
                logging.error(f"Database error: {e}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
            finally:
                conn.close()

    def _calculate_folders_size(self, folders: List[tuple], parent_path: str):
        """异步计算文件夹大小
        
        Args:
            folders: 需要计算大小的文件夹列表，每个元素是(文件夹名, 父项ID)的元组
            parent_path: 父级路径
        """
        try:
            # 显示蒙版
            self.app.after(0, self.app.show_overlay)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            total_folders = len(folders)
            for index, (folder_name, parent_item) in enumerate(folders, 1):
                # 更新状态栏和蒙版显示当前进度
                status_message = f"正在计算文件夹大小 ({index}/{total_folders}): {folder_name}"
                logging.debug(status_message)
                self.app.after(0, self.app.update_status, status_message)
                self.app.after(0, self.app.show_overlay, status_message)
                
                # 构建文件夹路径模式
                folder_path = f"{parent_path}{folder_name}/"
                if parent_path == '/':  # 避免双斜杠
                    folder_path = f"/{folder_name}/"
                
                # 简化的文件夹大小计算查询
                query = """
                SELECT SUM(file_size)
                FROM cache_file
                WHERE parent_path LIKE ? || '%'
                AND isdir = 0
                """
                
                cursor.execute(query, (folder_path,))
                total_size = cursor.fetchone()[0] or 0
                
                # 在UI线程中更新显示
                item = self._find_item_by_name(parent_item, folder_name)
                if item:
                    self.after(0, self._update_item_size, item, total_size)
            
            # 所有文件夹大小计算完毕
            completion_message = "文件夹大小计算完成"
            self.app.after(0, self.app.update_status, completion_message)
            self.app.after(0, self.app.hide_overlay)  # 隐藏蒙版
            
            # 更新图表
            selected_items = self.tree.selection()
            if selected_items:
                path = self._get_full_path(selected_items[0])
                self.app.after(0, lambda p=path: self.app._load_chart_data(p))
            
            conn.close()
            
        except sqlite3.Error as e:
            error_message = f"计算文件夹大小时发生数据库错误: {e}"
            logging.error(error_message)
            self.app.after(0, self.app.update_status, error_message)
            self.app.after(0, self.app.hide_overlay)
        except Exception as e:
            error_message = f"计算文件夹大小时发生错误: {e}"
            logging.error(error_message)
            self.app.after(0, self.app.update_status, error_message)
            self.app.after(0, self.app.hide_overlay)

    def _find_item_by_name(self, parent_item: str, name: str) -> Optional[str]:
        """根据名称查找树节点
        
        Args:
            parent_item: 父节点ID
            name: 节点名称
            
        Returns:
            Optional[str]: 找到的节点ID或None
        """
        for item in self.tree.get_children(parent_item):
            if self.tree.item(item)['text'] == name:
                return item
        return None

    def _update_item_size(self, item: str, size: int):
        """更新树节点的大小显示
        
        Args:
            item: 节点ID
            size: 文件大小
        """
        self.tree.set(item, 'size', self._format_size(size))

    def _trigger_chart_update(self, selected_item: str):
        """触发图表更新
        
        Args:
            selected_item: 当前选中的节点ID
        """
        path = self._get_full_path(selected_item)
        self.app.after(0, lambda p=path: self.app._load_chart_data(p))
    
    def _insert_item(self, parent: str, name: str, size: str, isdir: bool):
        """在树形视图中插入新项目
        
        Args:
            parent: 父级项目的ID
            name: 项目名称
            size: 格式化后的大小字符串
            isdir: 是否是目录
        """
        logging.debug(f"Inserting item: {name} under parent: {parent} (isdir={isdir})")
        try:
            # 存储项目类型信息
            item = self.tree.insert(parent, 'end', text=name, values=(size,))
            self.tree.set(item, 'isdir', isdir)  # 在树节点中存储isdir信息
            
            if isdir:
                # 添加临时子项
                dummy = self.tree.insert(item, 'end')
                logging.debug(f"Added dummy item to {name}")
        except Exception as e:
            logging.error(f"Error inserting item {name}: {e}")
    
    def _on_item_opened(self, event):
        """处理树节点展开事件
        
        当用户展开一个目录时，加载其子项目。
        """
        item = self.tree.focus()
        logging.debug(f"TreeviewOpen event triggered for item: {self.tree.item(item, 'text')}")
        
        # 如果节点已经加载过，就不再重复加载
        if item in self._loaded_nodes:
            logging.debug(f"Item already loaded: {self.tree.item(item, 'text')}")
            return
            
        # 获取当前子项
        children = self.tree.get_children(item)
        logging.debug(f"Current children count: {len(children)}")
        
        # 删除所有子项
        for child in children:
            logging.debug(f"Deleting child: {self.tree.item(child, 'text')}")
            self.tree.delete(child)
            
        # 获取完整路径
        path = self._get_full_path(item)
        logging.debug(f"Loading children for path: {path}")
        
        # 标记节点为已加载
        self._loaded_nodes.add(item)
        
        # 加载子项
        threading.Thread(target=self._load_items, args=(path, item)).start()
    
    def _get_full_path(self, item: str) -> str:
        """获取项目的完整路径
        
        Args:
            item: 项目ID
            
        Returns:
            str: 项目的完整路径，如果是目录则以'/'结尾
        """
        if not item or item == self.root_node:
            return '/'
            
        path_parts = []
        current = item
        is_dir = False
        
        # 收集路径部分并检查是否是目录
        while current and current != self.root_node:
            item_data = self.tree.item(current)
            text = item_data['text']
            # 检查第一个项目（当前项目）是否是目录
            if current == item:
                # 使用存储在树节点中的isdir信息
                is_dir = bool(self.tree.set(current, 'isdir'))
                logging.debug(f"Checking if '{text}' is directory: {is_dir}")
            path_parts.insert(0, text)
            current = self.tree.parent(current)
        
        # 构建完整路径
        full_path = '/' + '/'.join(path_parts)
        
        # 如果是目录且不以'/'结尾，添加'/'
        if is_dir and not full_path.endswith('/'):
            full_path += '/'
            
        logging.debug(f"Generated full path: {full_path} (is_dir={is_dir})")
        return full_path
    
    def get_selected_path(self) -> Optional[str]:
        """获取当前选中项目的路径
        
        Returns:
            Optional[str]: 选中项目的路径，如果没有选中项则返回None
        """
        selected = self.tree.selection()
        if not selected:
            logging.debug("No item selected")
            return None
        path = self._get_full_path(selected[0])
        logging.debug(f"Selected path: {path}")
        return path

    def find_node_by_path_and_name(self, parent_path: str, name: str) -> Optional[str]:
        """根据路径和名称查找树节点
        
        Args:
            parent_path: 父级路径
            name: 节点名称
            
        Returns:
            Optional[str]: 找到的节点ID或None
        """
        # 如果是根路径
        if parent_path == '/':
            for item in self.tree.get_children(self.root_node):
                if self.tree.item(item)['text'] == name:
                    return item
        else:
            # 先找到父节点
            parent_node = None
            for item in self.tree.get_children(self.root_node):
                current_path = self._get_full_path(item)
                if current_path == parent_path:
                    parent_node = item
                    break
            
            if parent_node:
                # 在父节点下查找目标节点
                for item in self.tree.get_children(parent_node):
                    if self.tree.item(item)['text'] == name:
                        return item
        return None

    def parse_size_str(self, size_str: str) -> int:
        """将大小字符串转换为字节数
        
        Args:
            size_str: 大小字符串（例如：'1.23 MB'）
            
        Returns:
            int: 字节数
        """
        if not size_str or size_str == "计算中...":
            return 0
            
        try:
            # 分离数值和单位
            parts = size_str.split()
            if len(parts) != 2:
                return 0
                
            value = float(parts[0])
            unit = parts[1]
            
            # 转换单位
            multipliers = {
                'B': 1,
                'KB': 1024,
                'MB': 1024 * 1024,
                'GB': 1024 * 1024 * 1024
            }
            
            if unit in multipliers:
                return int(value * multipliers[unit])
            
            return 0
            
        except (ValueError, IndexError):
            return 0

class PieChartFrame(ttk.Frame):
    """饼图显示框架"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # 创建标签用于显示总大小
        self.total_size_label = ttk.Label(
            self,
            text="",
            font=("Helvetica", 12, "bold")
        )
        self.total_size_label.pack(pady=5)
        
        # 创建Matplotlib图形
        self.figure = Figure(figsize=(6, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        
        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas.draw()
        
        # 获取画布的小部件并打包
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(expand=True, fill='both', padx=10, pady=10)
        
        # 存储当前数据
        self.current_data = None
        self.current_wedges = None
        self.selected_wedge = None
        self.last_click_time = 0
        self.last_clicked_index = None
        
        # 绑定事件 - 确保在画布创建后绑定
        self._bind_events()
        
        # 启用鼠标事件支持
        self.canvas.mpl_connect('button_press_event', self._on_click)
        self.canvas.draw_idle()
    
    def _bind_events(self):
        """绑定所有必要的事件"""
        # 绑定鼠标事件到画布
        self.canvas.callbacks.connect('button_press_event', self._on_click)
        
        # 使画布可以接收鼠标事件
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.bind('<Button-1>', lambda e: canvas_widget.focus_set())
        
        # 确保画布可以接收键盘焦点
        canvas_widget.config(takefocus=1)
    
    def _on_click(self, event):
        """处理点击事件"""
        logging.debug("Click event received")  # 添加调试日志
        
        if not event.inaxes:
            logging.debug("Click not in axes")
            return
            
        if not self.current_wedges:
            logging.debug("No current wedges")
            return
            
        current_time = time.time()
        
        # 检查是否点击了某个扇形
        for i, wedge in enumerate(self.current_wedges):
            contains, _ = wedge.contains(event)  # 使用contains方法检查
            if contains:
                logging.debug(f"Wedge {i} clicked")  # 添加调试日志
                
                # 检测双击
                if (i == self.last_clicked_index and 
                    (current_time - self.last_click_time) < 0.5):
                    logging.debug("Double click detected")  # 添加调试日志
                    self._handle_double_click(i)
                else:
                    logging.debug("Single click detected")  # 添加调试日志
                    self._handle_single_click(i, wedge)
                
                # 更新最后点击的信息
                self.last_click_time = current_time
                self.last_clicked_index = i
                break
    
    def _handle_single_click(self, index: int, wedge):
        """处理单击事件"""
        logging.debug(f"Single click on wedge {index}")
        # 重置之前选中的扇形
        if self.selected_wedge:
            self.selected_wedge.set_edgecolor('black')
            self.selected_wedge.set_linewidth(1)
        
        # 高亮当前选中的扇形
        wedge.set_edgecolor('red')
        wedge.set_linewidth(2)
        self.selected_wedge = wedge
        
        # 更新画布
        self.canvas.draw()
        
        # 如果点击的不是"其他"，且数据存在
        if (self.current_data and index < len(self.current_data) and 
            self.current_data[index]['server_filename'] != "其他"):
            # 获取对应的文件/文件夹信息
            item = self.current_data[index]
            logging.debug(f"Selected item: {item['server_filename']}")
            
            # 通知主应用程序处理选择
            if hasattr(self.master, '_on_pie_select'):
                self.master._on_pie_select(item)
    
    def _handle_double_click(self, index: int):
        """处理双击事件"""
        logging.debug(f"Double click on wedge {index}")
        if (self.current_data and index < len(self.current_data) and 
            self.current_data[index]['server_filename'] != "其他"):
            # 获取对应的文件/文件夹信息
            item = self.current_data[index]
            logging.debug(f"Double clicked item: {item['server_filename']}")
            
            # 通知主应用程序处理双击
            if hasattr(self.master, '_on_pie_double_click'):
                self.master._on_pie_double_click(item)
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小显示"""
        if size == 0:
            return "0 B"
        
        units = [
            (1024 * 1024 * 1024, 'GB'),
            (1024 * 1024, 'MB'),
            (1024, 'KB'),
            (1, 'B')
        ]
        
        for divisor, unit in units:
            if size >= divisor:
                value = size / divisor
                if unit == 'B':
                    return f"{int(value)} {unit}"
                return f"{value:.2f} {unit}"
        
        return f"{size} B"

    def update_chart(self, data: List[Dict]):
        """更新饼图显示"""
        if not data:
            self.ax.clear()
            self.canvas.draw()
            return
        
        # 保存当前数据
        self.current_data = []  # 重置数据列表
        
        # 过滤出大小大于0的项目并按大小排序
        items = [(item['server_filename'], item['file_size'], item) 
                for item in data 
                if item['file_size'] > 0]
        items.sort(key=lambda x: x[1], reverse=True)
        
        if not items:
            self.ax.clear()
            self.canvas.draw()
            return
        
        # 准备前10大项目的数据
        top_10_items = items[:10]
        other_size = sum(size for _, size, _ in items[10:])
        
        # 准备显示数据
        names = []
        sizes = []
        
        # 添加前10项
        for name, size, item in top_10_items:
            names.append(name)
            sizes.append(size)
            self.current_data.append(item)  # 保存完整的项目数据
        
        # 如果有其他项目，添加到列表中
        if other_size > 0:
            names.append("其他")
            sizes.append(other_size)
            # 为"其他"创建一个虚拟项
            self.current_data.append({
                'server_filename': "其他",
                'file_size': other_size,
                'isdir': False
            })
        
        total_size = sum(sizes)
        
        # 更新总大小标签
        self.total_size_label.configure(text=f"总大小: {self._format_size(total_size)}")
        
        # 计算百分比
        percentages = [size/total_size*100 for size in sizes]
        
        # 清除旧图
        self.ax.clear()
        
        # 准备标签（名称+大小）
        formatted_sizes = [self._format_size(size) for size in sizes]
        formatted_labels = [f'{name}\n{size}' for name, size in zip(names, formatted_sizes)]
        
        # 创建新的饼图
        wedges, texts, autotexts = self.ax.pie(
            percentages,
            labels=formatted_labels,
            autopct='%1.1f%%',
            startangle=90,
            counterclock=False,
            wedgeprops=dict(width=0.7),  # 设置为环形图
            textprops={'fontsize': 8},
            colors=plt.cm.Set3.colors,  # 使用与之前相似的配色
            pctdistance=0.85,  # 百分比标签的位置
            labeldistance=1.1  # 标签的位置
        )
        
        # 调整文本对齐方式
        for text in texts:
            text.set_horizontalalignment('center')
        
        # 存储wedges用于交互
        self.current_wedges = wedges
        
        # 在中心添加总大小
        self.ax.text(
            0, 0,
            f'总大小\n{self._format_size(total_size)}',
            ha='center',
            va='center',
            fontsize=10,
            fontweight='bold'
        )
        
        # 设置标题
        self.ax.set_title("文件大小分布", pad=20)
        
        # 更新画布
        self.canvas.draw()

class App(tk.Tk):
    """主应用程序窗口"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 配置窗口
        self.title("文件浏览器")
        self.geometry("1200x800")
        
        # 配置样式
        style = ttk.Style()
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0")
        style.configure("TButton", padding=6)
        
        # 创建主布局
        self._setup_layout()
        
        # 创建顶部工具栏
        self._create_toolbar()
        
        # 创建主要部件
        self._create_main_widgets()
        
        # 创建状态栏
        self._create_status_bar()
        
        # 创建蒙版（初始隐藏）
        self._create_overlay()
        
        # 绑定事件
        self.tree_frame.tree.bind('<<TreeviewSelect>>', self._on_select)
    
    def _setup_layout(self):
        """设置窗口布局"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
    
    def _create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,0), sticky="ew")
        
        open_button = ttk.Button(
            toolbar,
            text="打开数据库文件",
            command=self.show_file_dialog
        )
        open_button.pack(side='left', padx=10, pady=10)
    
    def _create_main_widgets(self):
        """创建主要的界面部件"""
        self.tree_frame = TreeFrame(self)
        self.tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.pie_frame = PieChartFrame(self)
        self.pie_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Label(
            self,
            text="就绪",
            relief=tk.SUNKEN,
            padding=5
        )
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
    
    def _create_overlay(self):
        """创建蒙版"""
        self.overlay = ttk.Frame(self)
        self.overlay.grid(row=0, column=0, rowspan=3, columnspan=2, sticky="nsew")
        self.overlay.grid_remove()
        
        self.overlay_label = ttk.Label(
            self.overlay,
            text="正在计算文件夹大小...",
            font=("Helvetica", 12)
        )
        self.overlay_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def show_overlay(self, message: str = "正在计算文件夹大小..."):
        """显示蒙版"""
        self.overlay_label.configure(text=message)
        self.overlay.grid()
        self.overlay.lift()
    
    def hide_overlay(self):
        """隐藏蒙版"""
        self.overlay.grid_remove()
    
    def show_file_dialog(self):
        """显示文件选择对话框"""
        file_path = filedialog.askopenfilename(
            title="选择数据库文件",
            filetypes=[("SQLite数据库", "*.db"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.tree_frame.set_database(file_path)
    
    def _on_select(self, event):
        """处理树形视图的选择事件"""
        path = self.tree_frame.get_selected_path()
        if not path or not self.tree_frame.db_path:
            return
        
        threading.Thread(target=self._load_chart_data, args=(path,)).start()
    
    def _load_chart_data(self, path: str):
        """加载选中目录的数据并更新饼图"""
        try:
            conn = sqlite3.connect(self.tree_frame.db_path)
            cursor = conn.cursor()
            
            query = """
            SELECT id, server_filename, file_size, isdir
            FROM cache_file
            WHERE parent_path = ?
            """
            
            cursor.execute(query, (path,))
            items = cursor.fetchall()
            
            data = []
            for item_id, filename, file_size, isdir in items:
                if isdir:
                    folder_node = self.tree_frame.find_node_by_path_and_name(path, filename)
                    if folder_node:
                        size_str = self.tree_frame.tree.set(folder_node, 'size')
                        file_size = self.tree_frame.parse_size_str(size_str)
                
                data.append({
                    'server_filename': filename,
                    'file_size': file_size,
                    'isdir': isdir
                })
            
            conn.close()
            
            self.after(0, lambda: self.pie_frame.update_chart(data))
            
        except Exception as e:
            logging.error(f"加载图表数据时发生错误: {e}")
            self.update_status(f"加载图表数据时发生错误: {e}")
    
    def update_status(self, message: str):
        """更新状态栏消息"""
        self.status_bar.configure(text=message)

    def _on_pie_select(self, item: Dict):
        """处理饼图选择事件
        
        Args:
            item: 选中的文件/文件夹信息
        """
        # 获取当前选中的路径
        current_path = self.tree_frame.get_selected_path()
        if not current_path:
            return
            
        # 在树形图中查找并选中对应的节点
        target_node = self.tree_frame.find_node_by_path_and_name(
            current_path,
            item['server_filename']
        )
        
        if target_node:
            # 选中节点并确保它可见
            self.tree_frame.tree.see(target_node)
            self.tree_frame.tree.selection_set(target_node)
            
            # 如果是文件夹，展开它
            if item['isdir']:
                self.tree_frame.tree.item(target_node, open=True)

    def _on_pie_double_click(self, item: Dict):
        """处理饼图双击事件
        
        Args:
            item: 选中的文件/文件夹信息
        """
        # 获取当前选中的路径
        current_path = self.tree_frame.get_selected_path()
        if not current_path:
            return
            
        # 在树形图中查找并选中对应的节点
        target_node = self.tree_frame.find_node_by_path_and_name(
            current_path,
            item['server_filename']
        )
        
        if target_node:
            # 选中节点并确保它可见
            self.tree_frame.tree.see(target_node)
            self.tree_frame.tree.selection_set(target_node)
            
            # 如果是文件夹，展开它并加载其内容
            if item['isdir']:
                # 确保节点已加载
                if target_node not in self.tree_frame._loaded_nodes:
                    path = self.tree_frame._get_full_path(target_node)
                    self.tree_frame._loaded_nodes.add(target_node)
                    # 删除所有子项
                    for child in self.tree_frame.tree.get_children(target_node):
                        self.tree_frame.tree.delete(child)
                    # 加载子项
                    threading.Thread(target=self.tree_frame._load_items, 
                                  args=(path, target_node)).start()
                
                # 展开节点
                self.tree_frame.tree.item(target_node, open=True)

if __name__ == "__main__":
    app = App()
    app.mainloop() 