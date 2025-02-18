from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
import re
import json
from pathlib import Path

@dataclass
class PreprocessorState:
    defines: Dict[str, bool]
    active_blocks: List[bool] = field(default_factory=lambda: [True])
    
    def is_active(self) -> bool:
        return all(self.active_blocks)

class ModuleDependencyAnalyzer:
    def __init__(self, source_dir: Path):
        self.source_dir = Path(source_dir)
        self.modules: Dict[str, Path] = {}
        self.programs: Dict[str, Path] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        
    def scan_files(self):
        """Scan directory for all module definitions and programs."""
        for f90_file in self.source_dir.glob("*.F90"):
            with open(f90_file) as f:
                content = f.read()
                # Find module definitions
                for match in re.finditer(r'(?i)module\s+(\w+)', content):
                    module_name = match.group(1).lower()
                    self.modules[module_name] = f90_file
                
                # Find program definitions
                for match in re.finditer(r'(?i)program\s+(\w+)', content):
                    program_name = match.group(1).lower()
                    self.programs[program_name] = f90_file
                    
    def analyze_dependencies(self):
        """Build dependency graph for all modules and programs."""
        # Analyze module dependencies
        for module_name, file_path in self.modules.items():
            self._analyze_file_dependencies(module_name, file_path)
            
        # Analyze program dependencies
        for program_name, file_path in self.programs.items():
            self._analyze_file_dependencies(program_name, file_path)
    
    def _analyze_file_dependencies(self, name: str, file_path: Path):
        """Analyze dependencies for a single file."""
        with open(file_path) as f:
            content = f.read()
            deps = set()
            # Find USE statements
            for match in re.finditer(r'(?i)use\s+(\w+)', content):
                used_module = match.group(1).lower()
                deps.add(used_module)
            self.dependencies[name] = deps
                
    def analyze_file(self, filename: str) -> List[str]:
        """Analyze a specific file and return required modules in order."""
        self.scan_files()
        self.analyze_dependencies()
        
        # Find which module or program this file defines
        target_name = None
        for module, path in self.modules.items():
            if path.name == filename:
                target_name = module
                break
                
        if target_name is None:
            for program, path in self.programs.items():
                if path.name == filename:
                    target_name = program
                    break
                    
        if target_name is None:
            return []
            
        # Get ordered list of dependencies
        needed = []
        visited = set()
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            for dep in self.dependencies.get(name, set()):
                visit(dep)
                if dep not in needed:
                    needed.append(dep)
            
        visit(target_name)
        needed.append(target_name)
        return needed

class PreprocessorParser:
    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"Loaded config: {config}")  # Debug
        
        config_section = config['preprocessor_config']
        self.state = PreprocessorState(defines=config_section.get('defines', {}))
        self.grid_params = config_section.get('grid_parameters', {})
    
    def parse_file(self, filepath: Path) -> str:
        """Parse file content considering preprocessor directives."""
        content = filepath.read_text()
        processed_lines = []
        
        print(f"\nProcessing file: {filepath}")  # Debug
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('#'):
                print(f"Processing directive: {line}")  # Debug
                print(f"Current active blocks before: {self.state.active_blocks}")  # Debug
                i = self._handle_preprocessor_directive(lines, i, processed_lines)
                print(f"Current active blocks after: {self.state.active_blocks}")  # Debug
            elif self.state.is_active():
                processed_lines.append(lines[i])  # Keep original line with whitespace
                if 'dimension' in line or 'allocatable' in line:  # Debug
                    print(f"Including line: {lines[i]}")  # Debug
            i += 1
            
        processed_content = '\n'.join(processed_lines)
        print("\nProcessed content:")  # Debug
        print(processed_content)  # Debug
        return processed_content
    
    def _handle_preprocessor_directive(self, lines: List[str], i: int, 
                                     processed_lines: List[str]) -> int:
        """Handle preprocessor directives and return next line index."""
        line = lines[i].strip()
        
        if line.startswith('#ifdef'):
            define = line.split()[-1]
            is_defined = self.state.defines.get(define, False)
            print(f"ifdef {define}: {is_defined}")  # Debug
            self.state.active_blocks.append(is_defined)
            
        elif line.startswith('#ifndef'):
            define = line.split()[-1]
            is_defined = not self.state.defines.get(define, False)
            print(f"ifndef {define}: {is_defined}")  # Debug
            self.state.active_blocks.append(is_defined)
            
        elif line.startswith('#if'):
            expr = line[3:].strip()
            result = self._evaluate_preprocessor_expression(expr)
            print(f"if {expr}: {result}")  # Debug
            self.state.active_blocks.append(result)
            
        elif line.startswith('#elif'):
            if self.state.active_blocks:
                self.state.active_blocks.pop()
                expr = line[5:].strip()
                result = self._evaluate_preprocessor_expression(expr)
                print(f"elif {expr}: {result}")  # Debug
                self.state.active_blocks.append(result)
            
        elif line.startswith('#else'):
            if self.state.active_blocks:
                current = self.state.active_blocks.pop()
                self.state.active_blocks.append(not current)
            
        elif line.startswith('#endif'):
            if self.state.active_blocks:
                self.state.active_blocks.pop()
        
        return i + 1
    
    def _evaluate_preprocessor_expression(self, expr: str) -> bool:
        """Evaluate preprocessor expressions."""
        # Replace defined() calls
        expr = re.sub(r'defined\((\w+)\)', 
                     lambda m: str(m.group(1) in self.state.defines), expr)
        
        # Replace && with and, || with or
        expr = expr.replace('&&', ' and ').replace('||', ' or ')
        
        # Replace define names with their values
        for define, value in self.state.defines.items():
            expr = re.sub(r'\b{}\b'.format(define), str(value), expr)
        
        try:
            print(f"Evaluating expression: {expr}")  # Debug
            return bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception as e:
            print(f"Warning: Could not evaluate preprocessor expression: {expr}")
            print(f"Error: {str(e)}")
            return False

    def get_value(self, param_name: str) -> Optional[int]:
        """Get value from either grid_parameters or defines."""
        if param_name in self.grid_params:
            return self.grid_params[param_name]
        if param_name in self.state.defines:
            return self.state.defines[param_name]
        return None

class EnhancedModuleAnalyzer:
    def __init__(self, source_root: str, config_file: str):
        self.source_root = Path(source_root)
        print(f"Initializing analyzer with root: {source_root}")  # Debug
        self.preprocessor = PreprocessorParser(config_file)
        self.processed_contents = {} 
    
    def analyze_module(self, filename: str) -> dict:
        """Analyze a file (module or program) with preprocessor handling."""
        # First analyze dependencies
        dep_analyzer = ModuleDependencyAnalyzer(self.source_root)
        unit_order = dep_analyzer.analyze_file(filename)
        
        print(f"\nDependency order for {filename}: {unit_order}")  # Debug
        
        # Save all processed contents for parameter lookup
        self.processed_contents = {}
        
        results = {}
        # Process units in dependency order
        for unit in unit_order:
            # Get the file for this unit (could be in modules or programs)
            unit_file = (dep_analyzer.modules.get(unit) or 
                        dep_analyzer.programs.get(unit))
            
            if not unit_file:
                print(f"Could not find file for {unit}")
                continue
                
            print(f"Processing unit: {unit}")
            processed_content = self.preprocessor.parse_file(unit_file)
            self.processed_contents[unit] = processed_content
            
            # Analyze memory usage
            memory_usage = self._analyze_memory_usage(processed_content)
            unit_result = {
                'name': unit,
                'file_path': str(unit_file),
                'memory_usage': memory_usage,
                'dependencies': self._find_dependencies(processed_content)
            }
            
            # Store result directly under unit name
            if unit in dep_analyzer.modules:
                results[unit] = {'module': unit_result}
            else:
                results[unit] = {'program': unit_result}
            
        return results
    
    def _analyze_memory_usage(self, content: str) -> dict:
        """Analyze memory usage in preprocessed content."""
        memory_info = {
            'static_arrays': [],
            'allocatable_arrays': [],
            'derived_types': []
        }
        
        # Track kind mappings
        kind_mappings = {}
        for match in re.finditer(r'(?i)use\s+iso_fortran_env\s*,\s*only\s*:([^!]*)', content):
            mappings = match.group(1)
            for mapping in re.finditer(r'(\w+)\s*=>\s*(\w+)', mappings):
                kind_mappings[mapping.group(1)] = mapping.group(2)
        
        # Analysis patterns - updated to handle more type formats
        patterns = {
            'static_arrays': r'(?i)real\s*\((\w+)\)\s*,\s*dimension\s*\(([^)]+)\)\s*::\s*(\w+)',
            'allocatable_arrays': r'(?i)real\s*\((\w+)\)\s*,\s*allocatable\s*::\s*(\w+)(?:\([,:]*\))?',
            'derived_types': r'(?i)type\s*\((\w+)\).*?::\s*(\w+)'
        }
        
        # Find parameter values (like n)
        param_values = {}
        for match in re.finditer(r'(?i)integer\s*,\s*parameter\s*::\s*(\w+)\s*=\s*(\d+)', content):
            param_values[match.group(1)] = int(match.group(2))
        
        print("\nAnalyzing patterns:")  # Debug
        for category, pattern in patterns.items():
            print(f"\nLooking for {category}")  # Debug
            print(f"Pattern: {pattern}")  # Debug
            for match in re.finditer(pattern, content):
                print(f"Found match: {match.groups()}")  # Debug
                if category == 'allocatable_arrays':
                    kind_param, name = match.groups()
                    # Look for matching allocate statement
                    alloc_pattern = rf'(?i)allocate\s*\({name}\s*\(([^)]+)\)\)'
                    alloc_match = re.search(alloc_pattern, content)
                    if alloc_match:
                        dims = alloc_match.group(1)
                        # Translate kind (RK -> real64)
                        actual_kind = kind_mappings.get(kind_param, kind_param)
                        size = self._calculate_array_size(dims, actual_kind)
                        memory_info[category].append({
                            'name': name,
                            'type': f"real({actual_kind})",
                            'dimensions': dims,
                            'estimated_size': size
                        })
                elif category == 'static_arrays':
                    type_param, dims, name = match.groups()
                    size = self._calculate_array_size(dims, type_param)
                    memory_info[category].append({
                        'name': name,
                        'type': type_param,
                        'dimensions': dims,
                        'estimated_size': size
                    })
                else:
                    name = match.group(1)
                    memory_info[category].append({'name': name})
        
        return memory_info

    def _collect_parameters(self, content: str) -> Dict[str, int]:
        """Collect all parameter definitions and their values."""
        params = {}
        # First add preprocessor defines
        params.update(self.preprocessor.state.defines)
        
        # Then look for Fortran parameters
        for match in re.finditer(r'(?i)integer\s*,\s*parameter\s*::\s*(\w+)\s*=\s*(\w+)', content):
            param_name = match.group(1)
            param_value = match.group(2)
            # If the value is another parameter, look it up
            if param_value in params:
                params[param_name] = params[param_value]
            else:
                try:
                    params[param_name] = int(param_value)
                except ValueError:
                    print(f"Could not convert {param_value} to integer")
        return params

    def _evaluate_range(self, range_expr: str, params: Dict[str, int]) -> int:
        """Evaluate a Fortran array range expression like '1:n' or '0:n-1'."""
        if ':' not in range_expr:
            return 1  # Single index
            
        start, end = [x.strip() for x in range_expr.split(':')]
        print(f"Evaluating range {start}:{end} with params {params}")
        
        # Replace parameters with their values
        for param, value in params.items():
            start = start.replace(param, str(value))
            end = end.replace(param, str(value))
        
        print(f"After substitution: {start}:{end}")
        
        # Create a safe dict for eval
        safe_dict = {
            "__builtins__": None,
            "abs": abs,
            "min": min,
            "max": max
        }
        
        try:
            start_val = int(eval(start, {"__builtins__": None}, safe_dict))
            end_val = int(eval(end, {"__builtins__": None}, safe_dict))
            size = end_val - start_val + 1
            print(f"Calculated size: {size}")
            return size
        except Exception as e:
            print(f"Could not evaluate range {start}:{end}: {str(e)}")
            print("Using default size")
            return 100  # Default size if we can't evaluate

    def _calculate_array_size(self, dims_str: str, type_str: str) -> int:
        """Calculate array size in bytes using grid parameters and defines."""
        type_sizes = {
            'c_double': 8,
            'c_float': 4,
            'real64': 8,
            'real32': 4,
            'int64': 8,
            'int32': 4
        }
        
        print(f"\nCalculating size for type {type_str} with dimensions {dims_str}")
        total_elements = 1
        
        # Collect all parameters from all processed contents
        params = {}
        for content in self.processed_contents.values():
            params.update(self._collect_parameters(content))

        # Process each dimension
        dims = [d.strip() for d in dims_str.split(',')]
        for dim in dims:
            print(f"Processing dimension: {dim}")
            size = self._evaluate_range(dim, params)
            print(f"Dimension size: {size}")
            total_elements *= size
        
        type_size = type_sizes.get(type_str, 8)
        total_size = total_elements * type_size
        print(f"Final calculation: {total_elements} elements * {type_size} bytes = {total_size} bytes")
        return total_size

    def _find_dependencies(self, content: str) -> List[str]:
        """Find module dependencies."""
        deps = []
        for match in re.finditer(r'(?i)use\s+(\w+)(?:\s*,\s*only\s*:)?', content):
            module_name = match.group(1)
            if module_name.lower() not in deps:  # avoid duplicates
                deps.append(module_name.lower())
        return deps

