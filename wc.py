import os
import sys
import threading
import webbrowser
from collections import Counter
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog

# 字体处理库 fontTools 的可选导入
try:
    from fontTools.subset import Subsetter, Options
    from fontTools.ttLib import TTFont, TTCollection
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False

# ==============================================================================
# 核心分析逻辑 (这部分没有变化)
# ==============================================================================

def process_file_content(content, stats):
    """处理文件内容，并更新统计数据字典。"""
    for char in content:
        if char == '\0' or char == '\ufffd' or (ord(char) < 32 and char not in '\t\n\r'):
            continue
        
        stats['all_chars'].append(char)
        
        if '\u4e00' <= char <= '\u9fff':
            stats['chinese_chars'].append(char)
        elif 'a' <= char.lower() <= 'z':
            stats['english_chars'].append(char)
        elif char == ' ':
            stats['space_chars'].append(char)
        elif not char.isspace():
            stats['punctuation_chars'].append(char)

def generate_report(stats, output_file_path, log_func):
    """根据收集到的统计数据生成报告文件。"""
    log_func(f"\n正在生成报告文件: {output_file_path}")
    try:
        # 在写入前确保目录存在
        output_dir = os.path.dirname(output_file_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            unique_chars = sorted(list(set(stats['all_chars'])))
            output_file.write("==================================================\n")
            output_file.write("1. 所有出现过的唯一字符\n")
            output_file.write("==================================================\n")
            output_file.write("".join(unique_chars))
            output_file.write("\n\n")

            top_50_chinese = Counter(stats['chinese_chars']).most_common(50)
            output_file.write("==================================================\n")
            output_file.write("2. 出现频率最高的50个中文字\n")
            output_file.write("==================================================\n")
            if top_50_chinese:
                for i, (char, count) in enumerate(top_50_chinese, 1):
                    output_file.write(f"第 {i:02d} 名: '{char}' - 出现 {count} 次\n")
            else:
                output_file.write("在扫描的文件中未找到任何中文字符。\n")
            output_file.write("\n")

            output_file.write("==================================================\n")
            output_file.write("3. 总体统计\n")
            output_file.write("==================================================\n")
            output_file.write(f"总中文字数: {len(stats['chinese_chars'])}\n")
            output_file.write(f"总英文字母数: {len(stats['english_chars'])}\n")
            output_file.write(f"总空格数: {len(stats['space_chars'])}\n")
            output_file.write(f"总标点符号数: {len(stats['punctuation_chars'])}\n")
            
        log_func(f"\n分析完成！统计信息已成功保存到文件：\n{output_file_path}")
        messagebox.showinfo("成功", f"分析完成！\n报告已保存到:\n{output_file_path}")

    except Exception as e:
        log_func(f"写入统计文件时发生严重错误: {e}")
        messagebox.showerror("错误", f"写入报告文件时发生错误:\n{e}")

def analyze_path(target_path, output_file_path, log_func):
    """分析主函数，log_func用于将信息输出到GUI界面。"""
    target_extensions = ('.css', '.py', '.rpy', '.txt', '.rpym', '.sh', '.js')
    # 这是排除列表，也就是黑名单。
    excluded_files = ['emoji_trie.py']
    
    stats = {
        'all_chars': [], 'chinese_chars': [], 'english_chars': [],
        'space_chars': [], 'punctuation_chars': []
    }
    
    log_func(f"开始分析: {target_path}")
    log_func(f"将查找以下类型的文件: {', '.join(target_extensions)}")
    log_func(f"将排除以下文件: {', '.join(excluded_files)}\n")

    if os.path.isfile(target_path):
        filename = os.path.basename(target_path)
        if filename.lower() in excluded_files:
            log_func(f"  -> 已跳过 (按规则排除): {target_path}")
        elif filename.lower().endswith(target_extensions):
            log_func(f"  正在处理文件: {target_path}")
            try:
                with open(target_path, 'r', encoding='utf-8', errors='replace') as file:
                    content = file.read()
                    process_file_content(content, stats)
            except Exception as e:
                log_func(f"    -> 警告: 读取文件 '{target_path}' 时发生错误: {e}，已跳过。")
        else:
            log_func(f"  -> 已跳过 (文件类型不匹配): {target_path}")

    elif os.path.isdir(target_path):
        log_func(f"开始递归扫描目录: {target_path}")
        for root, dirs, files in os.walk(target_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                if filename.lower() in excluded_files:
                    log_func(f"  -> 已跳过 (按规则排除): {file_path}")
                    continue

                if filename.lower().endswith(target_extensions):
                    log_func(f"  正在处理: {file_path}")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                            content = file.read()
                            process_file_content(content, stats)
                    except Exception as e:
                        log_func(f"    -> 警告: 读取文件 '{file_path}' 时发生未知错误: {e}，已跳过。")
    
    if not stats['all_chars']:
        log_func("\n分析完成，但未找到任何可供分析的内容。")
        messagebox.showwarning("提醒", "分析完成，但未找到任何可供分析的内容。")
        return

    generate_report(stats, output_file_path, log_func)
    # 返回统计到的唯一字符集
    return set(stats['all_chars'])

# ==============================================================================
# 新增的字体瘦身核心逻辑
# ==============================================================================

def subset_font(font_path, characters, output_dir, log_func):
    """
    使用 fontTools 对字体文件或字体集合进行子集化。
    """
    if not FONTTOOLS_AVAILABLE:
        log_func("错误: 未找到 fontTools 库，无法执行字体瘦身。")
        log_func("请通过 'pip install fonttools' 命令安装。")
        return False, "fontTools 库未安装"

    try:
        font_name = os.path.basename(font_path)
        name, ext = os.path.splitext(font_name)
        output_filename = f"{name}_subset{ext}"
        output_path = os.path.join(output_dir, output_filename)

        # 确保输出文件名唯一
        counter = 1
        while os.path.exists(output_path):
            output_filename = f"{name}_subset_{counter}{ext}"
            output_path = os.path.join(output_dir, output_filename)
            counter += 1

        log_func(f"\n正在处理字体文件: {font_name}")
        log_func(f"  -> 输出至: {output_path}")

        # 定义通用的子集化选项
        def get_options():
            options = Options()
            # 不设置flavor，保持原格式
            options.layout_features = ['*']
            options.glyph_names = True
            options.symbol_cmap = True
            options.legacy_cmap = True
            options.notdef_outline = True
            options.recommended_glyphs = True
            options.name_legacy = True
            options.drop_tables = []
            options.recalc_bounds = True
            options.recalc_timestamp = True
            options.canonical_order = True
            return options

        # 尝试作为字体集合 (TTC/OTC) 打开
        try:
            ttc = TTCollection(font_path)
            log_func(f"  -> 检测到字体集合，包含 {len(ttc.fonts)} 个字重。将对所有字重进行瘦身。")
            
            for i, font in enumerate(ttc.fonts):
                log_func(f"    -> 正在处理第 {i+1}/{len(ttc.fonts)} 个字重...")
                subsetter = Subsetter(options=get_options())
                subsetter.populate(text="".join(characters))
                subsetter.subset(font)
            
            ttc.save(output_path)

        except Exception as e:
            # 如果作为集合打开失败，则作为单个字体文件处理
            if "Cannot handle 'OTTO' fonts" in str(e) or "Not a TTC file" in str(e) or "Bad TTC header" in str(e):
                log_func(f"  -> 作为单个字体文件处理。")
                font = TTFont(font_path)
                subsetter = Subsetter(options=get_options())
                subsetter.populate(text="".join(characters))
                subsetter.subset(font)
                font.save(output_path)
            else:
                # 如果是其他未知错误，则向上抛出
                raise e

        original_size = os.path.getsize(font_path) / 1024
        new_size = os.path.getsize(output_path) / 1024
        log_func(f"  -> 瘦身完成: {original_size:.2f} KB -> {new_size:.2f} KB (节省 {(1 - new_size/original_size) * 100:.2f}%)")
        
        return True, None
    except Exception as e:
        log_func(f"  -> 错误: 处理字体 '{font_path}' 时发生错误: {e}")
        return False, str(e)


# ==============================================================================
# 新增的辅助函数
# ==============================================================================
def get_default_output_path():
    """
    智能获取默认输出路径。
    优先使用H盘根目录，如果H盘不存在，则使用程序所在目录。
    """
    primary_drive = "H:\\"
    if os.path.exists(primary_drive):
        return os.path.join(primary_drive, "统计信息.txt")
    else:
        # sys.argv[0] 是启动程序的路径 (无论是 .py 还是 .exe)
        # os.path.abspath 确保我们得到一个绝对路径
        # os.path.dirname 获取该路径所在的目录
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(exe_dir, "统计信息.txt")

# ==============================================================================
# GUI 界面部分
# ==============================================================================

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("文件字符统计与字体瘦身工具 v1.0")
        self.master.geometry("800x600")
        self.master.configure(bg='#f0f0f0')
        self.configure(bg='#f0f0f0')
        self.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 初始化数据存储变量
        self.font_files = []
        self.unique_chars = set()
        self.extra_chars = set()

        self.create_widgets()
        self.update_button_states()

        if not FONTTOOLS_AVAILABLE:
            self.log("注意: 未找到 'fonttools' 库。字体瘦身功能将被禁用。")
            self.log("请在命令行中使用 'pip install fonttools' 来安装。")

    def create_widgets(self):
        # --- 标题和GitHub按钮 ---
        header_frame = tk.Frame(self, bg='#f0f0f0')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(header_frame, text="📊 字符统计与字体瘦身工具",
                               font=('Microsoft YaHei UI', 14, 'bold'),
                               bg='#f0f0f0', fg='#333')
        title_label.pack(side=tk.LEFT)
        
        self.github_button = tk.Button(header_frame, text="📂 GitHub",
                                       command=self.open_github,
                                       bg="#24292e", fg="white",
                                       font=('Arial', 9), relief=tk.FLAT,
                                       cursor="hand2", padx=10)
        self.github_button.pack(side=tk.RIGHT, padx=5)
        
        # --- 路径选择 ---
        path_frame = tk.LabelFrame(self, text="· 扫描内容选择",
                                   font=('Microsoft YaHei UI', 10, 'bold'),
                                   bg='#f0f0f0', fg='#333', padx=10, pady=5)
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.target_path_label = tk.Label(path_frame, text="目标文件/目录:", bg='#f0f0f0')
        self.target_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.target_path_var = tk.StringVar()
        self.target_path_entry = tk.Entry(path_frame, textvariable=self.target_path_var,
                                          width=50, font=('Consolas', 9))
        self.target_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.browse_target_button = tk.Button(path_frame, text="📁 浏览",
                                              command=self.browse_target,
                                              bg="#607D8B", fg="white", relief=tk.FLAT, cursor="hand2")
        self.browse_target_button.pack(side=tk.LEFT, padx=5, pady=5)

        # --- 字体文件选择 ---
        font_frame = tk.LabelFrame(self, text="· 字体文件选择 (可选)",
                                   font=('Microsoft YaHei UI', 10, 'bold'),
                                   bg='#f0f0f0', fg='#333', padx=10, pady=5)
        font_frame.pack(fill=tk.X, padx=5, pady=5)

        self.font_listbox = tk.Listbox(font_frame, selectmode=tk.EXTENDED, height=4,
                                       font=('Consolas', 9), bg='#ffffff')
        self.font_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        font_button_frame = tk.Frame(font_frame, bg='#f0f0f0')
        font_button_frame.pack(side=tk.LEFT, padx=5)
        self.add_font_button = tk.Button(font_button_frame, text="➕ 添加字体",
                                         command=self.add_fonts,
                                         bg="#4CAF50", fg="white", relief=tk.FLAT, cursor="hand2")
        self.add_font_button.pack(fill=tk.X, pady=2)
        self.remove_font_button = tk.Button(font_button_frame, text="➖ 移除选中",
                                           command=self.remove_fonts,
                                           bg="#f44336", fg="white", relief=tk.FLAT, cursor="hand2")
        self.remove_font_button.pack(fill=tk.X, pady=2)

        # --- 输出设置 ---
        output_frame = tk.LabelFrame(self, text="· 输出设置",
                                     font=('Microsoft YaHei UI', 10, 'bold'),
                                     bg='#f0f0f0', fg='#333', padx=10, pady=5)
        output_frame.pack(fill=tk.X, padx=5, pady=5)

        # 报告输出
        report_output_frame = tk.Frame(output_frame, bg='#f0f0f0')
        report_output_frame.pack(fill=tk.X, expand=True, pady=2)
        self.output_path_label = tk.Label(report_output_frame, text="报告保存位置:", bg='#f0f0f0', width=12, anchor='w')
        self.output_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.output_path_var = tk.StringVar(value=get_default_output_path())
        self.output_path_entry = tk.Entry(report_output_frame, textvariable=self.output_path_var,
                                          width=40, font=('Consolas', 9))
        self.output_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.browse_output_button = tk.Button(report_output_frame, text="💾 选择",
                                              command=self.browse_output,
                                              bg="#607D8B", fg="white", relief=tk.FLAT, cursor="hand2")
        self.browse_output_button.pack(side=tk.LEFT, padx=5, pady=5)

        # 字体输出
        font_output_frame = tk.Frame(output_frame, bg='#f0f0f0')
        font_output_frame.pack(fill=tk.X, expand=True, pady=2)
        self.font_output_path_label = tk.Label(font_output_frame, text="字体保存目录:", bg='#f0f0f0', width=12, anchor='w')
        self.font_output_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.font_output_path_var = tk.StringVar()
        self.font_output_path_entry = tk.Entry(font_output_frame, textvariable=self.font_output_path_var,
                                               width=40, font=('Consolas', 9))
        self.font_output_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.browse_font_output_button = tk.Button(font_output_frame, text="📁 选择",
                                                   command=self.browse_font_output,
                                                   bg="#607D8B", fg="white", relief=tk.FLAT, cursor="hand2")
        self.browse_font_output_button.pack(side=tk.LEFT, padx=5, pady=5)

        # --- 控制按钮 ---
        control_frame = tk.Frame(self, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.start_button = tk.Button(control_frame, text="▶ 开始分析",
                                      command=self.start_analysis,
                                      bg="#4CAF50", fg="white",
                                      font=('Microsoft YaHei UI', 11, 'bold'),
                                      relief=tk.FLAT, cursor="hand2", height=2)
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        self.extra_chars_button = tk.Button(control_frame, text="✏ 额外字符",
                                            command=self.add_extra_chars,
                                            bg="#FF9800", fg="white",
                                            font=('Microsoft YaHei UI', 10),
                                            relief=tk.FLAT, cursor="hand2", height=2)
        self.extra_chars_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        self.subset_button = tk.Button(control_frame, text="✂ 字体瘦身",
                                       command=self.start_subsetting,
                                       bg="#2196F3", fg="white",
                                       font=('Microsoft YaHei UI', 11, 'bold'),
                                       relief=tk.FLAT, cursor="hand2", height=2)
        self.subset_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        self.clear_log_button = tk.Button(control_frame, text="🗑 清空日志",
                                          command=self.clear_log,
                                          bg="#9E9E9E", fg="white",
                                          font=('Microsoft YaHei UI', 10),
                                          relief=tk.FLAT, cursor="hand2", height=2)
        self.clear_log_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        # --- 日志输出 ---
        log_frame = tk.LabelFrame(self, text="📋 日志输出",
                                  font=('Microsoft YaHei UI', 10, 'bold'),
                                  bg='#f0f0f0', fg='#333', padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled',
                                                  font=('Consolas', 9), bg='#ffffff')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部版权信息
        footer_frame = tk.Frame(self, bg='#f0f0f0')
        footer_frame.pack(fill=tk.X, pady=(5, 0))
        footer_label = tk.Label(footer_frame,
                               text=" 字符统计与字体瘦身工具 ",
                               font=('Arial', 8), bg='#f0f0f0', fg='#666')
        footer_label.pack()
    
    def open_github(self):
        """打开GitHub项目页面"""
        webbrowser.open("https://github.com/AxelBeary/Word-count-and-text-removal")
        self.log("已在浏览器中打开GitHub项目页面。")

    def browse_target(self):
        path = filedialog.askdirectory()
        if not path:
            path = filedialog.askopenfilename()
        if path:
            self.target_path_var.set(path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="统计信息.txt",
            title="选择报告保存位置"
        )
        if path:
            self.output_path_var.set(path)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.master.update_idletasks()

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def update_button_states(self):
        """根据当前状态更新按钮的可用性"""
        analysis_done = bool(self.unique_chars)
        fonts_selected = bool(self.font_files)
        
        # 额外字符按钮：分析完成后可用
        self.extra_chars_button.config(state=tk.NORMAL if analysis_done else tk.DISABLED)
        
        # 字体瘦身按钮：分析完成、有字体文件、安装了fontTools库后可用
        can_subset = analysis_done and fonts_selected and FONTTOOLS_AVAILABLE
        self.subset_button.config(state=tk.NORMAL if can_subset else tk.DISABLED)
        
        # 字体输出路径选择：安装了fontTools库后可用
        font_output_state = tk.NORMAL if FONTTOOLS_AVAILABLE else tk.DISABLED
        self.font_output_path_entry.config(state=font_output_state)
        self.browse_font_output_button.config(state=font_output_state)

    def add_fonts(self):
        """添加一个或多个字体文件"""
        files = filedialog.askopenfilenames(
            title="选择字体文件",
            filetypes=[("字体文件", "*.ttf *.otf"), ("所有文件", "*.*")]
        )
        if files:
            for file in files:
                if file not in self.font_files:
                    self.font_files.append(file)
                    self.font_listbox.insert(tk.END, os.path.basename(file))
            self.log(f"添加了 {len(files)} 个字体文件。")
            self.update_button_states()

    def remove_fonts(self):
        """移除选中的字体文件"""
        selected_indices = self.font_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("提示", "请先在列表中选择要移除的字体文件。")
            return
            
        # 从后往前删除，避免索引错乱
        for i in sorted(selected_indices, reverse=True):
            self.font_listbox.delete(i)
            removed_file = self.font_files.pop(i)
            self.log(f"移除了字体文件: {os.path.basename(removed_file)}")
        self.update_button_states()

    def browse_font_output(self):
        """选择字体瘦身后的保存目录"""
        path = filedialog.askdirectory(title="选择瘦身字体的保存目录")
        if path:
            self.font_output_path_var.set(path)

    def add_extra_chars(self):
        """弹出对话框，让用户手动添加字符"""
        # 创建一个自定义对话框
        dialog = tk.Toplevel(self.master)
        dialog.title("添加额外字符")
        dialog.geometry("400x300")
        
        tk.Label(dialog, text="在此处输入需要额外保留的字符:").pack(pady=5)
        
        text_area = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, height=10)
        text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        text_area.focus_set()

        def on_ok():
            new_chars = set(text_area.get(1.0, tk.END).strip())
            if new_chars:
                original_count = len(self.extra_chars)
                self.extra_chars.update(new_chars)
                new_added_count = len(self.extra_chars) - original_count
                self.log(f"添加了 {new_added_count} 个新的唯一额外字符。")
                total_chars = len(self.unique_chars) + len(self.extra_chars)
                self.log(f"当前总字符集大小: {total_chars}")
            dialog.destroy()

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        # 模态对话框
        dialog.transient(self.master)
        dialog.grab_set()
        self.master.wait_window(dialog)

    def start_analysis(self):
        target_path = self.target_path_var.get()
        output_path = self.output_path_var.get()

        if not target_path or not output_path:
            messagebox.showerror("错误", "必须同时指定目标路径和报告保存位置！")
            return

        self.start_button.config(state='disabled', text="正在分析...")
        self.browse_target_button.config(state='disabled')
        self.browse_output_button.config(state='disabled')
        
        analysis_thread = threading.Thread(
            target=self.run_analysis_thread,
            args=(target_path, output_path)
        )
        analysis_thread.start()

    def start_subsetting(self):
        """开始执行字体瘦身"""
        font_output_dir = self.font_output_path_var.get()
        if not font_output_dir:
            messagebox.showerror("错误", "请先选择瘦身字体的保存目录！")
            return
        
        if not os.path.isdir(font_output_dir):
            messagebox.showerror("错误", "选择的字体保存目录无效或不存在！")
            return

        combined_chars = self.unique_chars.union(self.extra_chars)
        if not combined_chars:
            messagebox.showwarning("提示", "字符集为空，无法进行字体瘦身。")
            return

        self.log(f"\n--- 开始字体瘦身 ---")
        self.log(f"总计 {len(combined_chars)} 个唯一字符将被保留。")
        self.log(f"字体将保存到: {font_output_dir}")

        # 禁用按钮
        self.start_button.config(state='disabled')
        self.subset_button.config(state='disabled', text="正在瘦身...")
        
        subsetting_thread = threading.Thread(
            target=self.run_subsetting_thread,
            args=(self.font_files[:], combined_chars, font_output_dir) # 传入副本
        )
        subsetting_thread.start()

    def run_subsetting_thread(self, font_paths, characters, output_dir):
        """在单独的线程中执行字体瘦身"""
        try:
            success_count = 0
            fail_count = 0
            for font_path in font_paths:
                success, error_msg = subset_font(font_path, characters, output_dir, self.log)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
            
            self.log(f"\n--- 字体瘦身完成 ---")
            self.log(f"成功: {success_count} 个, 失败: {fail_count} 个。")
            messagebox.showinfo("完成", f"字体瘦身处理完成！\n成功: {success_count}, 失败: {fail_count}")

        except Exception as e:
            self.log(f"字体瘦身过程中发生严重错误: {e}")
            messagebox.showerror("严重错误", f"字体瘦身过程中断:\n{e}")
        finally:
            # 恢复按钮状态
            self.start_button.config(state='normal')
            self.subset_button.config(state='normal', text="字体瘦身")
            self.update_button_states()

    def run_analysis_thread(self, target_path, output_path):
        try:
            # 清空上一次的分析结果
            self.unique_chars.clear()
            self.log("清空旧的字符集统计。")

            # analyze_path 现在会返回字符集
            result_chars = analyze_path(target_path, output_path, self.log)
            if result_chars:
                self.unique_chars = result_chars
                self.log(f"\n分析完成，共找到 {len(self.unique_chars)} 个唯一字符。")
                # 自动设置字体输出目录为报告所在目录
                report_dir = os.path.dirname(output_path)
                self.font_output_path_var.set(report_dir)
                self.log(f"默认字体输出目录已设置为: {report_dir}")

        except Exception as e:
            self.log(f"发生了一个未预料的严重错误: {e}")
            messagebox.showerror("严重错误", f"分析过程中断:\n{e}")
        finally:
            self.start_button.config(state='normal', text="开始分析")
            self.browse_target_button.config(state='normal')
            self.browse_output_button.config(state='normal')
            self.update_button_states()

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()