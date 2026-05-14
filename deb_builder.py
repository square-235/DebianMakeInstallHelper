import os
import subprocess
import shutil
from pathlib import Path
from cmake_parser import CMakeParser

class DebPackageBuilder:
    def __init__(self, source_dir):
        self.source_dir = Path(source_dir).resolve()
        self.deb_dir = None
        self.deb_path = None
        self.pkg_name = None
        self.install_prefix = "/usr"
    
    def check_cmakelist(self):
        cmake_file = self.source_dir / "CMakeLists.txt"
        return cmake_file.exists()
    
    def parse_cmake_install(self):
        cmake_file = self.source_dir / "CMakeLists.txt"
        build_dir = self.source_dir / "build"
        parser = CMakeParser(cmake_file, build_dir)
        parser.parse()
        
        if 'CMAKE_INSTALL_PREFIX' in parser.variables:
            self.install_prefix = parser.variables['CMAKE_INSTALL_PREFIX']
        elif build_dir.exists():
            cache_file = build_dir / "CMakeCache.txt"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    for line in f:
                        if line.startswith('CMAKE_INSTALL_PREFIX:'):
                            parts = line.split('=', 1)
                            if len(parts) > 1:
                                self.install_prefix = parts[1].strip()
                                break
        
        return parser.install_rules
    
    def run_compile_commands_streaming(self, commands, callback):
        valid_commands = [cmd.strip() for cmd in commands if cmd.strip()]
        
        if not valid_commands:
            callback("No commands to execute\n")
            return False
        
        full_command = " && ".join(valid_commands)
        
        try:
            process = subprocess.Popen(
                full_command,
                shell=True,
                cwd=self.source_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for cmd in valid_commands:
                callback(f"$ {cmd}\n")
            
            while True:
                line = process.stdout.readline()
                if line:
                    callback(line)
                else:
                    break
            
            process.wait()
            
            callback(f"\nReturn code: {process.returncode}\n")
            
            if process.returncode != 0:
                return False
            return True
        except Exception as e:
            callback(f"Error executing commands: {e}\n")
            return False
    
    def run_compile_commands(self, commands):
        success = True
        output = []
        valid_commands = [cmd.strip() for cmd in commands if cmd.strip()]
        
        if not valid_commands:
            return False, "No commands to execute"
        
        full_command = " && ".join(valid_commands)
        
        try:
            result = subprocess.run(
                full_command,
                shell=True,
                cwd=self.source_dir,
                capture_output=True,
                text=True
            )
            
            for cmd in valid_commands:
                output.append(f"Command: {cmd}")
            
            output.append(f"STDOUT:\n{result.stdout}")
            output.append(f"STDERR:\n{result.stderr}")
            output.append(f"Return code: {result.returncode}")
            
            if result.returncode != 0:
                success = False
        except Exception as e:
            output.append(f"Error executing commands: {e}")
            success = False
        
        return success, "\n".join(output)
    
    def find_binary_files(self):
        binaries = []
        exclude_patterns = [
            'a.out',
            'CMakeDetermineCompilerABI_',
            'CMakeCompilerId',
            'CMakeTest',
            '_test',
            '_tests',
            '.test.',
            'Test',
            'Testing',
        ]
        
        build_dir = self.source_dir / "build"
        search_dirs = [build_dir] if build_dir.exists() else [self.source_dir]
        
        for search_dir in search_dirs:
            for root, dirs, files in os.walk(search_dir):
                dirs[:] = [d for d in dirs if d not in ['Testing', '.git', 'CMakeFiles']]
                
                for file in files:
                    if any(pattern in file for pattern in exclude_patterns):
                        continue
                    
                    filepath = Path(root) / file
                    try:
                        if os.access(filepath, os.X_OK) and filepath.is_file():
                            with open(filepath, 'rb') as f:
                                header = f.read(4)
                                if header.startswith(b'\x7fELF'):
                                    binaries.append(filepath)
                    except:
                        pass
        
        return binaries
    
    def run_make_install_in_chroot(self, install_cmd, callback):
        pkg_name = self.source_dir.name.lower().replace('_', '-').replace(' ', '-')
        self.deb_dir = self.source_dir / "deb_package"
        
        if self.deb_dir.exists():
            shutil.rmtree(self.deb_dir)
        
        self.deb_dir.mkdir(parents=True)
        
        dirs_to_create = [
            'bin', 'etc', 'lib', 'sbin', 'usr/bin', 'usr/lib', 
            'usr/share', 'var', 'usr/local/bin', 'usr/local/lib'
        ]
        
        for d in dirs_to_create:
            (self.deb_dir / d).mkdir(parents=True, exist_ok=True)
        
        callback(f"(需要在终端输入密码)创建 chroot 环境: {self.deb_dir}\n")
        
        build_dir = self.source_dir / "build"
        if not build_dir.exists():
            build_dir = self.source_dir
        
        if install_cmd.startswith('sudo '):
            cmd = f"sudo DESTDIR={self.deb_dir} {install_cmd[5:]}"
        else:
            cmd = install_cmd
        
        env = os.environ.copy()
        env['DESTDIR'] = str(self.deb_dir)
        
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=build_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            callback(f"$ DESTDIR={self.deb_dir} {install_cmd}\n")
            callback(f"工作目录: {build_dir}\n")
            
            while True:
                line = process.stdout.readline()
                if line:
                    callback(line)
                else:
                    break
            
            process.wait()
            
            callback(f"\nReturn code: {process.returncode}\n")
            
            if process.returncode != 0:
                return False
            return True
        except Exception as e:
            callback(f"Error executing commands: {e}\n")
            return False
    
    def _calculate_installed_size(self):
        total_size = 0
        for root, dirs, files in os.walk(self.deb_dir):
            for file in files:
                filepath = Path(root) / file
                if filepath.is_file():
                    total_size += filepath.stat().st_size
        
        return total_size // 1024
        
    def create_deb_structure(self, binaries, install_dir="/opt", version="1.0.0"):
        pkg_name = self.source_dir.name.lower().replace('_', '-').replace(' ', '-')
        self.pkg_name = pkg_name
        self.pkg_version = version
        
        if self.deb_dir is None or not self.deb_dir.exists():
            self.deb_dir = self.source_dir / "deb_package"
            if self.deb_dir.exists():
                shutil.rmtree(self.deb_dir)
            
            deb_install_path = self.deb_dir / install_dir.lstrip('/') / pkg_name
            deb_install_path.mkdir(parents=True)
            
            for binary in binaries:
                shutil.copy2(binary, deb_install_path / binary.name)
        
        deb_control = self.deb_dir / "DEBIAN"
        if deb_control.exists():
            shutil.rmtree(deb_control)
        deb_control.mkdir()
        
        pkg_arch = "amd64"
        
        installed_size = self._calculate_installed_size()
        
        control_content = f"""Package: {pkg_name}
Version: {version}
Architecture: {pkg_arch}
Maintainer: User <user@example.com>
Description: Compiled from source at {self.source_dir}
Priority: optional
Installed-Size: {installed_size}
"""
        
        (deb_control / "control").write_text(control_content)
        
        prefix_sh = self.source_dir / "build" / "prefix.sh"
        if prefix_sh.exists():
            postinst = deb_control / "postinst"
            shutil.copy2(prefix_sh, postinst)
            postinst.chmod(0o755)
        
        return pkg_name, str(self.deb_dir)
    
    def build_deb(self):
        if not self.deb_dir or not self.pkg_name:
            return False, "Deb structure not created"
        
        version = getattr(self, 'pkg_version', "1.0.0")
        self.deb_path = self.source_dir / f"{self.pkg_name}_{version}_amd64.deb"
        cmd = f"dpkg-deb --build {self.deb_dir} {self.deb_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and self.deb_path.exists():
            return True, str(self.deb_path)
        return False, result.stderr
    
    def install_deb(self):
        if not self.deb_path or not self.deb_path.exists():
            return False, "Deb package not found"
        
        cmd = f"sudo dpkg -i {self.deb_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, "Package installed successfully"
        return False, result.stderr