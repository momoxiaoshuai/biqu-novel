import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QListWidget,
                            QLabel, QProgressBar, QMessageBox, QListWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from biqu import NovelDownloader

class DownloadWorker(QThread):
    progress = pyqtSignal(int, int)  # 当前章节，总章节
    finished = pyqtSignal(bool, str)  # 成功/失败，消息
    
    def __init__(self, url, novel_name, author):
        super().__init__()
        self.url = url
        self.novel_name = novel_name
        self.author = author
        self.downloader = NovelDownloader()
        
    def update_progress(self, current, total):
        self.progress.emit(current, total)
        
    def run(self):
        try:
            self.downloader.set_progress_callback(self.update_progress)
            result = self.downloader.download_novel(self.url, self.novel_name, self.author)
            if result:
                self.finished.emit(True, f"《{self.novel_name}》下载完成！")
            else:
                self.finished.emit(False, "下载失败")
        except Exception as e:
            self.finished.emit(False, f"下载出错: {str(e)}")

class SearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, keyword):
        super().__init__()
        self.keyword = keyword
        self.downloader = NovelDownloader()
        
    def run(self):
        try:
            results = self.downloader.search(self.keyword)
            if not results or results == 1:
                self.error.emit("未找到相关小说")
            else:
                self.finished.emit(results)
        except Exception as e:
            self.error.emit(f"搜索出错: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("笔趣阁小说下载器")
        self.setMinimumSize(600, 400)
        
        # 设置应用图标
        icon_path = os.path.join(os.path.dirname(__file__), "alien.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 创建主窗口部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入小说名称")
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.search_novel)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)
        
        # 搜索结果列表
        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self.download_selected)
        layout.addWidget(self.result_list)
        
        # 下载进度区域
        progress_layout = QHBoxLayout()
        
        progress_info_layout = QVBoxLayout()
        self.progress_label = QLabel("准备就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_info_layout.addWidget(self.progress_label)
        progress_info_layout.addWidget(self.progress_bar)
        
        self.cancel_button = QPushButton("取消下载")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        
        progress_layout.addLayout(progress_info_layout)
        progress_layout.addWidget(self.cancel_button)
        layout.addLayout(progress_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #e1e4e8;
                border-radius: 6px;
                font-size: 14px;
                background-color: white;
                color: #24292e;
                outline: none;
            }
            QLineEdit:focus {
                border-color: #0366d6;
                box-shadow: 0 0 0 3px rgba(3, 102, 214, 0.3);
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #2ea44f;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2c974b;
            }
            QPushButton:pressed {
                background-color: #2a8f47;
            }
            QPushButton:disabled {
                background-color: #94d3a2;
            }
            QListWidget {
                border: 1px solid #e1e4e8;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                background-color: white;
                selection-background-color: #0366d6;
                selection-color: white;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #f6f8fa;
            }
            QListWidget::item:selected {
                background-color: #e1e4e8;
                color: #24292e;
            }
            QLabel {
                font-size: 14px;
                color: #24292e;
                padding: 4px;
            }
            QProgressBar {
                border: 1px solid #e1e4e8;
                border-radius: 4px;
                text-align: center;
                background-color: #f6f8fa;
                outline: none;
            }
            QProgressBar::chunk {
                background-color: #2ea44f;
                border-radius: 3px;
            }
        """)
        
        # 添加窗口边距
        main_widget = self.centralWidget()
        main_widget.setContentsMargins(20, 20, 20, 20)
        layout = main_widget.layout()
        layout.setSpacing(15)
        
        # 设置搜索区域的边距
        search_layout = layout.itemAt(0).layout()
        search_layout.setSpacing(10)
        
        # 美化搜索框
        self.search_input.setMinimumHeight(36)
        self.search_button.setMinimumHeight(36)
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 美化列表
        self.result_list.setAlternatingRowColors(True)
        self.result_list.setStyleSheet(self.result_list.styleSheet() + """
            QListWidget {
                alternate-background-color: #f8f9fa;
            }
        """)
        
        self.search_input.returnPressed.connect(self.search_novel)
        
        # 搜索按钮样式
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #0366d6;  /* GitHub蓝色 */
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0255b3;
            }
            QPushButton:pressed {
                background-color: #024494;
            }
            QPushButton:disabled {
                background-color: #80b3ff;
            }
        """)
        
    def search_novel(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入小说名称")
            return
            
        self.search_button.setEnabled(False)
        self.result_list.clear()
        self.progress_label.setText("搜索中...")
        
        self.search_worker = SearchWorker(keyword)
        self.search_worker.finished.connect(self.handle_search_results)
        self.search_worker.error.connect(self.handle_search_error)
        self.search_worker.finished.connect(
            lambda: self.search_button.setEnabled(True))
        self.search_worker.start()
        
    def handle_search_results(self, results):
        self.result_list.clear()
        for i, item in enumerate(results, 1):
            list_item = QListWidgetItem(
                f"{i}. 《{item['articlename']}》 作者：{item['author']}")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.result_list.addItem(list_item)
        self.progress_label.setText(f"找到 {len(results)} 个结果")
        
    def handle_search_error(self, error_msg):
        self.progress_label.setText(error_msg)
        self.search_button.setEnabled(True)
        
    def download_selected(self, item):
        novel_data = item.data(Qt.ItemDataRole.UserRole)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认下载")
        msg_box.setText(f"是否下载《{novel_data['articlename']}》？")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        # 获取按钮并设置样式
        yes_button = msg_box.button(QMessageBox.StandardButton.Yes)
        no_button = msg_box.button(QMessageBox.StandardButton.No)
        
        # 确认按钮使用绿色（与下载按钮一致）
        yes_button.setStyleSheet("""
            QPushButton {
                background-color: #2ea44f;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2c974b;
            }
            QPushButton:pressed {
                background-color: #2a8f47;
            }
        """)
        
        # 取消按钮使用灰色
        no_button.setStyleSheet("""
            QPushButton {
                background-color: #6e7681;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #636d76;
            }
            QPushButton:pressed {
                background-color: #575e67;
            }
        """)
        
        yes_button.setText("下载")
        no_button.setText("取消")
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.start_download(novel_data)
            
    def start_download(self, novel_data):
        url = f"https://www.biqg.cc{novel_data['url_list']}"
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.cancel_button.setVisible(True)  # 显示取消按钮
        self.progress_label.setText(f"正在下载《{novel_data['articlename']}》...")
        
        self.download_worker = DownloadWorker(
            url, novel_data['articlename'], novel_data['author'])
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.finished.connect(self.handle_download_finished)
        self.download_worker.start()
        
    def cancel_download(self):
        reply = QMessageBox.question(
            self, 
            "确认取消", 
            "确定要取消下载吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_worker.downloader.cancel_download()
            self.progress_label.setText("正在取消下载...")
            self.cancel_button.setEnabled(False)
        
    def handle_download_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)  # 隐藏取消按钮
        self.cancel_button.setEnabled(True)   # 重置按钮状态
        self.progress_label.setText(message)
        
        if success:
            QMessageBox.information(self, "下载完成", message)
        else:
            if self.download_worker.downloader.is_cancelled:
                self.progress_label.setText("下载已取消")
            else:
                QMessageBox.warning(self, "下载失败", message)
        
    def update_progress(self, current, total):
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"正在下载: {current}/{total} 章 ({percentage}%)")

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序图标（在任务栏显示）
    icon_path = os.path.join(os.path.dirname(__file__), "alien.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 