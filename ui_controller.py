import threading
import re
from pathlib import Path
import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QApplication
from deb_builder import DebPackageBuilder
from stream_signals import StreamSignals

class MainWindowController:
    def __init__(self, ui):
        self.ui = ui
        self.source_dir = ""
        self.builder = None
        self.binaries = []
        
        self.connect_signals()
    
    def connect_signals(self):
        self.ui.browse_btn.clicked.connect(self.browse_dir)
        self.ui.compile_btn.clicked.connect(self.run_compile)
        self.ui.package_btn.clicked.connect(self.run_package)
        self.ui.install_btn.clicked.connect(self.run_install)
    
    def browse_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, "选择源码目录")
        if dir_path:
            self.source_dir = dir_path
            self.ui.dir_edit.setText(dir_path)
            
            self.builder = DebPackageBuilder(dir_path)
            self.ui.status_label.setText("状态: 已选择目录")
            self.ui.compile_btn.setEnabled(True)
            
            deb_package_dir = Path(dir_path) / "deb_package"
            if deb_package_dir.exists() and deb_package_dir.is_dir():
                self.ui.package_btn.setEnabled(True)
            
            for deb_file in Path(dir_path).glob("*.deb"):
                if deb_file.is_file():
                    self.ui.install_btn.setEnabled(True)
                    break
    
    def add_output(self, text):
        self.ui.output_text.append(text)
        self.ui.output_text.verticalScrollBar().setValue(self.ui.output_text.verticalScrollBar().maximum())
        QApplication.processEvents()
    
    def run_compile(self):
        if not self.source_dir or not self.builder:
            return
        
        commands = self.ui.cmd_text.toPlainText().strip().split('\n')
        commands = [c for c in commands if c.strip() and not c.strip().startswith('#')]
        
        if not commands:
            QMessageBox.warning(None, "警告", "请输入编译命令")
            return
        
        processed_commands = []
        install_cmd = None
        
        for cmd in commands:
            cmd_stripped = cmd.strip()
            
            if cmd_stripped.endswith('make install') or cmd_stripped.endswith('sudo make install'):
                install_cmd = cmd_stripped
                continue
            
            if cmd_stripped == 'make':
                processed_commands.append('make -j$(nproc)')
            else:
                processed_commands.append(cmd_stripped)
        
        self.ui.output_text.clear()
        
        if install_cmd:
            self.add_output(f"⚠️ 检测到安装命令: {install_cmd}")
            self.add_output(f"⚠️ 将使用 DESTDIR 方式拦截，不会直接安装到系统\n")
        
        self.ui.status_label.setText("状态: 正在执行编译命令...")
        self.ui.compile_btn.setEnabled(False)
        self.ui.package_btn.setEnabled(False)
        
        version = self.ui.version_edit.text().strip()
        if not version:
            version = "1.0.0"
        
        self.signals = StreamSignals()
        self.signals.output.connect(self.add_output)
        
        if install_cmd:
            self.signals.finished.connect(lambda success: self.on_compile_finished(success, install_cmd, version))
        else:
            self.signals.finished.connect(lambda success: self.on_compile_finished(success, None, version))
        
        def compile_thread():
            if processed_commands:
                success = self.builder.run_compile_commands_streaming(processed_commands, self.signals.output.emit)
            else:
                success = True
            self.signals.finished.emit(success)
        
        threading.Thread(target=compile_thread, daemon=True).start()
    
    def on_compile_finished(self, success, install_cmd, version="1.0.0"):
        if not success:
            self.ui.status_label.setText("状态: 编译失败")
            QMessageBox.critical(None, "错误", "编译失败，请查看输出")
            self.ui.compile_btn.setEnabled(True)
            return
        
        if install_cmd:
            self.ui.status_label.setText("状态: 使用 DESTDIR 执行安装...")
            QApplication.processEvents()
            
            success = self.builder.run_make_install_in_chroot(install_cmd, self.add_output)
            
            if not success:
                self.ui.status_label.setText("状态: 安装失败")
                QMessageBox.critical(None, "错误", "安装失败，请查看输出")
                self.ui.compile_btn.setEnabled(True)
                return
            
            self.ui.status_label.setText("状态: 安装成功，创建Deb包结构...")
            QApplication.processEvents()
            
            pkg_name = self.source_dir.lower().replace('_', '-').replace(' ', '-')
            deb_path = str(self.builder.deb_dir)
            
            self.add_output(f"\n创建Deb包结构: {pkg_name}")
            self.add_output(f"Deb目录: {deb_path}")
            
            deb_files = []
            for root, dirs, files in os.walk(deb_path):
                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(deb_path)
                    deb_files.append(str(rel_path))
            
            if deb_files:
                self.add_output("\nDeb包内容:")
                for f in sorted(deb_files):
                    if f != 'DEBIAN/control':
                        self.add_output(f"  {f}")
            
            pkg_name, deb_path = self.builder.create_deb_structure([], version=version)
        else:
            self.ui.status_label.setText("状态: 编译成功，查找二进制文件...")
            QApplication.processEvents()
            
            self.binaries = self.builder.find_binary_files()
            if not self.binaries:
                self.add_output("\n错误: 未找到二进制文件")
                self.ui.status_label.setText("状态: 未找到二进制文件")
                QMessageBox.critical(None, "错误", "未找到编译生成的二进制文件")
                self.ui.compile_btn.setEnabled(True)
                return
            
            self.add_output(f"\n找到 {len(self.binaries)} 个二进制文件:")
            for b in self.binaries:
                self.add_output(f"  {b}")
            
            self.ui.status_label.setText("状态: 创建Deb包结构...")
            QApplication.processEvents()
            
            pkg_name, deb_path = self.builder.create_deb_structure(self.binaries, "/opt", version=version)
            self.add_output(f"\n创建Deb包结构: {pkg_name}")
            self.add_output(f"Deb目录: {deb_path}")
            
            deb_files = []
            for root, dirs, files in os.walk(deb_path):
                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(deb_path)
                    deb_files.append(str(rel_path))
            
            if deb_files:
                self.add_output("\nDeb包内容:")
                for f in sorted(deb_files):
                    self.add_output(f"  {f}")
        
        self.ui.status_label.setText("状态: Deb结构已创建，可进行打包")
        self.ui.package_btn.setEnabled(True)
        self.ui.compile_btn.setEnabled(True)
    
    def run_package(self):
        if not self.builder:
            return
        
        if not self.builder.deb_dir or not self.builder.deb_dir.exists():
            deb_package_dir = Path(self.source_dir) / "deb_package"
            if deb_package_dir.exists() and deb_package_dir.is_dir():
                self.builder.deb_dir = deb_package_dir
                self.builder.pkg_name = Path(self.source_dir).name.lower().replace('_', '-').replace(' ', '-')
                version = self.ui.version_edit.text().strip()
                if version:
                    self.builder.pkg_version = version
        
        self.ui.status_label.setText("状态: 构建Deb包...")
        self.ui.package_btn.setEnabled(False)
        QApplication.processEvents()
        
        success, msg = self.builder.build_deb()
        if not success:
            self.add_output(f"\n错误: {msg}")
            self.ui.status_label.setText("状态: Deb包构建失败")
            QMessageBox.critical(None, "错误", f"Deb包构建失败: {msg}")
            self.ui.package_btn.setEnabled(True)
            return
        
        self.add_output(f"\nDeb包创建成功: {msg}")
        self.ui.status_label.setText("状态: Deb包已创建")
        self.ui.install_btn.setEnabled(True)
        self.ui.package_btn.setEnabled(True)
    
    def run_install(self):
        if not self.builder:
            return
        
        if not self.builder.deb_path or not self.builder.deb_path.exists():
            for deb_file in Path(self.source_dir).glob("*.deb"):
                if deb_file.is_file():
                    self.builder.deb_path = deb_file
                    break
        
        self.ui.status_label.setText("状态: 安装Deb包...")
        self.ui.install_btn.setEnabled(False)
        QApplication.processEvents()
        
        success, msg = self.builder.install_deb()
        if success:
            self.add_output(f"\n{msg}")
            self.ui.status_label.setText("状态: 安装成功")
            QMessageBox.information(None, "成功", "Deb包安装成功")
        else:
            self.add_output(f"\n安装失败: {msg}")
            self.ui.status_label.setText("状态: 安装失败")
            QMessageBox.critical(None, "错误", f"安装失败: {msg}")
        
        self.ui.install_btn.setEnabled(True)