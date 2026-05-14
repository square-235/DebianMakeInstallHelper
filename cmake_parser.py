import re
from pathlib import Path

class CMakeParser:
    def __init__(self, cmake_file, build_dir=None):
        self.cmake_file = cmake_file
        self.build_dir = build_dir
        self.install_rules = []
        self.variables = {}
    
    def parse(self):
        self._parse_cmakelists()
        
        if self.build_dir and self.build_dir.exists():
            install_cmake = self.build_dir / "cmake_install.cmake"
            if install_cmake.exists():
                self._parse_cmake_install(install_cmake)
    
    def _parse_cmakelists(self):
        if not self.cmake_file.exists():
            return
        
        with open(self.cmake_file, 'r') as f:
            content = f.read()
        
        content = self._remove_comments(content)
        
        var_pattern = r'set\s*\(\s*([A-Za-z0-9_]+)\s+([^\)]+)\s*\)'
        matches = re.finditer(var_pattern, content)
        for match in matches:
            var_name = match.group(1).strip()
            var_value = match.group(2).strip()
            self.variables[var_name] = var_value
        
        install_patterns = [
            r'install\s*\(\s*TARGETS\s+([^)]+)\s*\)',
            r'install\s*\(\s*TARGETS\s+([^)]+)\s+DESTINATION\s+([^\s)]+)\s*\)',
            r'install\s*\(\s*FILES\s+([^)]+)\s*\)',
            r'install\s*\(\s*FILES\s+([^)]+)\s+DESTINATION\s+([^\s)]+)\s*\)',
            r'install\s*\(\s*PROGRAMS\s+([^)]+)\s*\)',
            r'install\s*\(\s*PROGRAMS\s+([^)]+)\s+DESTINATION\s+([^\s)]+)\s*\)',
            r'install\s*\(\s*DIRECTORY\s+([^)]+)\s*\)',
            r'install\s*\(\s*DIRECTORY\s+([^)]+)\s+DESTINATION\s+([^\s)]+)\s*\)',
        ]
        
        for pattern in install_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                rule = {'type': pattern.split('\\(')[1].split('\\s')[0].lower()}
                if len(match.groups()) >= 1:
                    rule['targets'] = [t.strip() for t in match.group(1).split()]
                if len(match.groups()) >= 2:
                    rule['destination'] = match.group(2).strip()
                else:
                    rule['destination'] = 'bin'
                self.install_rules.append(rule)
    
    def _parse_cmake_install(self, install_cmake):
        with open(install_cmake, 'r') as f:
            content = f.read()
        
        content = self._remove_comments(content)
        
        install_pattern = r'file\s*\(\s*INSTALL\s+DESTINATION\s+"([^"]+)"\s+TYPE\s+(\w+)\s+FILES\s+"([^"]+)"\s*\)'
        matches = re.finditer(install_pattern, content)
        
        for match in matches:
            dest = match.group(1)
            file_type = match.group(2)
            src_file = match.group(3)
            
            dest = self._expand_variables(dest)
            
            rule = {
                'type': file_type.lower(),
                'destination': dest,
                'files': [src_file],
                'from_cmake_install': True
            }
            self.install_rules.append(rule)
    
    def _expand_variables(self, text):
        while True:
            match = re.search(r'\$\{([A-Za-z0-9_]+)\}', text)
            if not match:
                break
            var_name = match.group(1)
            var_value = self.variables.get(var_name, '')
            text = text.replace(f'${{{var_name}}}', var_value)
        return text
    
    def _remove_comments(self, content):
        lines = content.split('\n')
        result = []
        
        for line in lines:
            if '#' in line:
                line = line[:line.index('#')]
            result.append(line)
        
        return '\n'.join(result)