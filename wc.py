import os
import sys
import threading
from collections import Counter
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

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
        self.master.title("文件字符统计工具")
        self.master.geometry("700x500")
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.create_widgets()

    def create_widgets(self):
        # --- 路径选择 ---
        path_frame = tk.LabelFrame(self, text="路径选择")
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.target_path_label = tk.Label(path_frame, text="目标文件/目录:")
        self.target_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.target_path_var = tk.StringVar()
        self.target_path_entry = tk.Entry(path_frame, textvariable=self.target_path_var, width=50)
        self.target_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.browse_target_button = tk.Button(path_frame, text="浏览...", command=self.browse_target)
        self.browse_target_button.pack(side=tk.LEFT, padx=5, pady=5)

        output_frame = tk.LabelFrame(self, text="输出设置")
        output_frame.pack(fill=tk.X, padx=5, pady=5)

        self.output_path_label = tk.Label(output_frame, text="报告保存位置:")
        self.output_path_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # --- 这里是主要修改点 ---
        self.output_path_var = tk.StringVar()
        # 在创建输入框前，调用函数设置默认值
        self.output_path_var.set(get_default_output_path()) 
        self.output_path_entry = tk.Entry(output_frame, textvariable=self.output_path_var, width=50)
        self.output_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.browse_output_button = tk.Button(output_frame, text="选择位置...", command=self.browse_output)
        self.browse_output_button.pack(side=tk.LEFT, padx=5, pady=5)

        # --- 控制按钮 ---
        control_frame = tk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=10)
        self.start_button = tk.Button(control_frame, text="开始分析", command=self.start_analysis, bg="#4CAF50", fg="white", font=('Helvetica', 10, 'bold'))
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.clear_log_button = tk.Button(control_frame, text="清空日志", command=self.clear_log)
        self.clear_log_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # --- 日志输出 ---
        log_frame = tk.LabelFrame(self, text="日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

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

    def run_analysis_thread(self, target_path, output_path):
        try:
            analyze_path(target_path, output_path, self.log)
        except Exception as e:
            self.log(f"发生了一个未预料的严重错误: {e}")
            messagebox.showerror("严重错误", f"分析过程中断:\n{e}")
        finally:
            self.start_button.config(state='normal', text="开始分析")
            self.browse_target_button.config(state='normal')
            self.browse_output_button.config(state='normal')

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()