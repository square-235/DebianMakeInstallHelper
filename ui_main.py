from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

class MainWindowUI:
    def setup_ui(self, window):
        window.setWindowTitle("源码编译与Deb打包工具")
        window.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self.info_label = QLabel("""<b>使用说明:</b>
此程序可以方便地在Debian系发行版帮你从源码编译安装软件。
它会自动使用chroot拦截sudo make install命令，一键将编译好的程序转换成deb包安装，以解决使用make安装软件包后管理困难的问题。"""
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        self.info_label = QLabel("""注意:程序执行到一些命令需要授权，请在终端中输入密码。apt安装依赖请使用-y参数（最好在外部终端执行）。""")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)

        self.info_label = QLabel("""也能用于打包：工作目录存在deb_package文件夹即可使用打包按钮""")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.info_label)


        self.dir_layout = QHBoxLayout()
        self.dir_label = QLabel("源码目录:")
        self.dir_label.setFixedWidth(80)
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("选择源码目录")
        self.browse_btn = QPushButton("浏览")
        self.dir_layout.addWidget(self.dir_label)
        self.dir_layout.addWidget(self.dir_edit)
        self.dir_layout.addWidget(self.browse_btn)
        layout.addLayout(self.dir_layout)
        
        self.version_layout = QHBoxLayout()
        self.version_label = QLabel("版本号:")
        self.version_label.setFixedWidth(80)
        self.version_edit = QLineEdit()
        self.version_edit.setText("1.0.0")
        self.version_layout.addWidget(self.version_label)
        self.version_layout.addWidget(self.version_edit)
        layout.addLayout(self.version_layout)
        
        self.cmd_label = QLabel("编译命令 (每行一个命令):")
        layout.addWidget(self.cmd_label)
        
        self.cmd_text = QTextEdit()
        self.cmd_text.setPlaceholderText("输入编译命令")
        self.cmd_text.setText("# 示例编译命令\n#需要装依赖先使用apt\n#需要克隆代码可选择空目录使用git clone再cd过去\nmkdir -p build\ncd build\ncmake ..\nmake -j$(nproc)\nsudo make install\n#make install命令会自动拦截到chroot，输出到./deb_package下，随后可转换为deb包安装")
        layout.addWidget(self.cmd_text)
        
        self.status_label = QLabel("状态: 等待选择目录")
        self.status_label.setStyleSheet("color: blue;")
        layout.addWidget(self.status_label)
        
        self.output_label = QLabel("输出日志:")
        layout.addWidget(self.output_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)
        
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(10)
        
        self.compile_btn = QPushButton("开始编译")
        self.compile_btn.setEnabled(False)
        self.button_layout.addWidget(self.compile_btn)
        
        self.package_btn = QPushButton("打包成Deb")
        self.package_btn.setEnabled(False)
        self.button_layout.addWidget(self.package_btn)
        
        self.install_btn = QPushButton("安装Deb包")
        self.install_btn.setEnabled(False)
        self.button_layout.addWidget(self.install_btn)
        
        layout.addLayout(self.button_layout)
