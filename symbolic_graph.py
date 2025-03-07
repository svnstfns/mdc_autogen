import os
import re
import astroid
from astroid import nodes
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def is_standard_library(module_name):
    """Check if a module is part of the Python standard library."""
    # List of common standard library modules
    stdlib_modules = {
        "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib", 
        "copy", "csv", "datetime", "enum", "functools", "glob", "gzip", "hashlib", 
        "io", "itertools", "json", "logging", "math", "os", "pathlib", "pickle", 
        "random", "re", "shutil", "socket", "sqlite3", "string", "struct", "subprocess", 
        "sys", "tempfile", "threading", "time", "traceback", "typing", "unittest", 
        "urllib", "uuid", "xml", "zipfile"
    }
    
    # Check if it's a direct standard library module
    if module_name in stdlib_modules:
        return True
    
    # Check if it's a submodule of a standard library module
    main_module = module_name.split('.')[0]
    return main_module in stdlib_modules


def resolve_import(import_name, current_file, repo_path):
    """Attempt to resolve an import to an actual file in the repository."""
    # Skip standard library imports
    if is_standard_library(import_name):
        return None
        
    # Skip known third-party packages
    known_packages = {
        "numpy", "pandas", "matplotlib", "sklearn", "tensorflow", "torch", "requests", 
        "django", "flask", "fastapi", "sqlalchemy", "pytest", "openai", "astroid", 
        "networkx", "pydantic", "git", "esprima", "instructor"
    }
    main_module = import_name.split('.')[0]
    if main_module in known_packages:
        return None
    
    # Try to resolve as a file within the repo
    parts = import_name.split(".")
    
    # Debug output
    print("Resolving import: {} from file: {}".format(import_name, current_file))
    
    # For project-specific imports like 'src.*', we need to find the actual src directory
    if parts[0] == 'src':
        # Try to find the src directory by walking up from the current file
        if current_file:
            current_dir = os.path.dirname(os.path.abspath(current_file))
            # Walk up the directory tree looking for 'src'
            while current_dir and current_dir != os.path.dirname(current_dir):  # Stop at root
                if os.path.basename(current_dir) == 'src':
                    # We found the src directory itself
                    potential_path = current_dir
                    for part in parts[1:]:  # Skip the 'src' part
                        potential_path = os.path.join(potential_path, part)
                    
                    # Check if it's a Python file
                    if os.path.isfile(potential_path + ".py"):
                        return os.path.relpath(potential_path + ".py", repo_path)
                    
                    # Check if it's a directory with __init__.py
                    if os.path.isdir(potential_path) and os.path.isfile(os.path.join(potential_path, "__init__.py")):
                        return os.path.relpath(os.path.join(potential_path, "__init__.py"), repo_path)
                    
                    break
                
                # Check if there's a src directory at this level
                src_dir = os.path.join(current_dir, 'src')
                if os.path.isdir(src_dir):
                    # We found a src directory
                    potential_path = src_dir
                    for part in parts[1:]:  # Skip the 'src' part
                        potential_path = os.path.join(potential_path, part)
                    
                    # Check if it's a Python file
                    if os.path.isfile(potential_path + ".py"):
                        return os.path.relpath(potential_path + ".py", repo_path)
                    
                    # Check if it's a directory with __init__.py
                    if os.path.isdir(potential_path) and os.path.isfile(os.path.join(potential_path, "__init__.py")):
                        return os.path.relpath(os.path.join(potential_path, "__init__.py"), repo_path)
                    
                    break
                
                # Move up one directory
                current_dir = os.path.dirname(current_dir)
    
    # Try to find the module directly from repo_path
    # This handles both project-specific imports and regular imports
    potential_paths = [
        # Direct from repo root
        os.path.join(repo_path, *parts),
        # From potential src directory
        os.path.join(repo_path, "src", *parts[1:]) if parts[0] == "src" else None,
        # From backend directory (common in web projects)
        os.path.join(repo_path, "backend", *parts) if parts[0] != "backend" else None,
        os.path.join(repo_path, "backend", "src", *parts[1:]) if parts[0] == "src" else None,
    ]
    
    # Filter out None values
    potential_paths = [p for p in potential_paths if p]
    
    # Check each potential path
    for potential_path in potential_paths:
        # Check for .py file
        if os.path.isfile(potential_path + ".py"):
            return os.path.relpath(potential_path + ".py", repo_path)
            
        # Check for directory with __init__.py
        if os.path.isdir(potential_path) and os.path.isfile(os.path.join(potential_path, "__init__.py")):
            return os.path.relpath(os.path.join(potential_path, "__init__.py"), repo_path)
    
    # Try different combinations of the import path
    for i in range(len(parts), 0, -1):
        potential_path = os.path.join(repo_path, *parts[:i])
        
        # Check for direct .py file
        if os.path.isfile(potential_path + ".py"):
            return os.path.relpath(potential_path + ".py", repo_path)
            
        # Check for directory with __init__.py
        if os.path.isdir(potential_path) and os.path.isfile(os.path.join(potential_path, "__init__.py")):
            return os.path.relpath(os.path.join(potential_path, "__init__.py"), repo_path)
    
    # Handle relative imports relative to the current file
    if current_file:
        current_dir = os.path.dirname(current_file)
        # Try joining with the current directory
        potential_path = os.path.join(current_dir, *parts)
        if os.path.isfile(potential_path + ".py"):
            return os.path.relpath(potential_path + ".py", repo_path)
        if os.path.isdir(potential_path) and os.path.isfile(os.path.join(potential_path, "__init__.py")):
            return os.path.relpath(os.path.join(potential_path, "__init__.py"), repo_path)
    
    # If we get here, we couldn't resolve the import
    print("Could not resolve import: {}".format(import_name))
    return None


def analyze_js_ts_with_regex(file_path, repo_path, G):
    """
    Analyze JavaScript/TypeScript file dependencies using regex patterns.
    
    This is a fallback method when both esprima and ESLint are not available.
    Less accurate but better than nothing.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logging.error("Error reading file {}: {}".format(file_path, e))
        return
    
    relative_path = os.path.relpath(file_path, repo_path)
    
    # Regex patterns to match different types of imports
    import_patterns = [
        # ES6 imports: import X from 'path'
        r"import\s+(?:[\w\s{},*]+\s+from\s+)?['\"]([^'\"]+)['\"]",
        # CommonJS require: const x = require('path')
        r"require\s*\(\s*['\"]([^'\"]+)['\"]",
        # Dynamic imports: import('path')
        r"import\s*\(\s*['\"]([^'\"]+)['\"]",
        # Add pattern for CSS/SCSS imports
        r"@import\s+['\"]([^'\"]+)['\"]",
        # Add pattern for image/asset imports
        r"(?:src|href|url)\s*=\s*['\"]([^'\"]+\.(?:png|jpg|jpeg|gif|svg|webp|ico))['\"]"
    ]
    
    imports = []
    for pattern in import_patterns:
        matches = re.findall(pattern, content)
        imports.extend(matches)
    
    # Check for path aliases in tsconfig.json or package.json
    aliases = {}
    tsconfig_path = os.path.join(repo_path, "tsconfig.json")
    package_json_path = os.path.join(repo_path, "package.json")
    
    # Try to load tsconfig.json for path mappings
    if os.path.exists(tsconfig_path):
        try:
            import json
            with open(tsconfig_path, "r", encoding="utf-8") as f:
                tsconfig = json.load(f)
                if "compilerOptions" in tsconfig and "paths" in tsconfig["compilerOptions"]:
                    paths = tsconfig["compilerOptions"]["paths"]
                    for alias, targets in paths.items():
                        # Remove wildcards for simple matching
                        clean_alias = alias.replace("/*", "")
                        if targets and len(targets) > 0:
                            # Use the first target path
                            target = targets[0].replace("/*", "")
                            aliases[clean_alias] = target
        except Exception as e:
            logging.error(f"Error parsing tsconfig.json: {e}")
    
    # Try to load package.json for aliases
    if os.path.exists(package_json_path):
        try:
            import json
            with open(package_json_path, "r", encoding="utf-8") as f:
                package_json = json.load(f)
                if "alias" in package_json:
                    for alias, target in package_json["alias"].items():
                        aliases[alias] = target
        except Exception as e:
            logging.error(f"Error parsing package.json: {e}")
    
    for imported_path in imports:
        # Skip built-in modules and third-party packages
        if not imported_path.startswith('.') and not imported_path.startswith('/') and not any(imported_path.startswith(alias) for alias in aliases):
            continue
        
        # Check if this import uses an alias
        resolved_path = imported_path
        for alias, target in aliases.items():
            if imported_path.startswith(alias):
                # Replace the alias with its target path
                resolved_path = imported_path.replace(alias, target, 1)
                break
        
        # Resolve the import path
        target_path = None
        import_dir = os.path.dirname(file_path)
        
        if resolved_path.startswith('./'):
            target_path = os.path.join(import_dir, resolved_path[2:])
        elif resolved_path.startswith('../'):
            parts = resolved_path.split('/')
            up_levels = 0
            for part in parts:
                if part == '..':
                    up_levels += 1
                else:
                    break
            
            current_dir = import_dir
            for _ in range(up_levels):
                current_dir = os.path.dirname(current_dir)
            
            target_path = os.path.join(current_dir, '/'.join(parts[up_levels:]))
        elif resolved_path.startswith('/'):
            # Absolute import within the project
            target_path = os.path.join(repo_path, resolved_path.lstrip('/'))
        elif resolved_path.startswith('~'):
            # Some frameworks use ~ to refer to the src directory
            target_path = os.path.join(repo_path, 'src', resolved_path[1:].lstrip('/'))
        elif resolved_path.startswith('@'):
            # Handle @/ imports (common in Vue.js and some React setups)
            target_path = os.path.join(repo_path, 'src', resolved_path[2:])
        else:
            # Try to resolve from repo root
            target_path = os.path.join(repo_path, resolved_path)
        
        if not target_path:
            continue
            
        # Handle extension-less imports
        extensions_to_check = ['.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.css', '.scss', '.less']
        
        # First check if the path exists exactly as specified
        if os.path.exists(target_path):
            target = os.path.relpath(target_path, repo_path)
            if target not in G.nodes():
                G.add_node(target, type="file")
            G.add_edge(relative_path, target, type="js_import")
            continue
            
        # Check with extensions
        found = False
        for ext in extensions_to_check:
            if os.path.exists(target_path + ext):
                target = os.path.relpath(target_path + ext, repo_path)
                if target not in G.nodes():
                    G.add_node(target, type="file")
                G.add_edge(relative_path, target, type="js_import")
                found = True
                break
        
        if found:
            continue
            
        # Check for directory with index file
        for index_file in ['index.js', 'index.jsx', 'index.ts', 'index.tsx', 'index.vue', 'index.svelte']:
            index_path = os.path.join(target_path, index_file)
            if os.path.exists(index_path):
                target = os.path.relpath(index_path, repo_path)
                if target not in G.nodes():
                    G.add_node(target, type="file")
                G.add_edge(relative_path, target, type="js_import")
                found = True
                break
                
        # If we still haven't found the file, log it
        if not found:
            logging.debug(f"Could not resolve JS/TS import: {imported_path} from {file_path}")


def analyze_imports_and_usage(file_path, repo_path, G):
    """Analyze imports and function/class usage in a Python file."""
    try:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()

        relative_path = os.path.relpath(file_path, repo_path)

        # Add node for this file if it doesn't exist
        if relative_path not in G.nodes():
            G.add_node(relative_path, type="file")
        
        # For Python files, use AST to analyze imports
        if file_path.endswith(".py"):
            try:
                # Parse the file with astroid for better import resolution
                module = astroid.parse(content)
                
                # Process imports and add edges to the graph
                for node in module.body:
                    # print(f"\033[91m{node}\033[0m")
                    # Handle regular imports: import foo, bar
                    if isinstance(node, nodes.Import):
                        for name, alias in node.names:
                            # Try to resolve the import to an actual file
                            resolved_path = resolve_import(name, file_path, repo_path)
                            print("\033[93m{} -> {}\033[0m".format(name, resolved_path))
                            if resolved_path:
                                G.add_edge(relative_path, resolved_path, type="import")
                                
                    # Handle from imports: from foo import bar, baz
                    elif isinstance(node, nodes.ImportFrom):
                        import_path = None
                        if node.level and node.level > 0:  # Handle relative imports, check if level is not None
                            # Calculate the path for relative imports
                            current_dir = os.path.dirname(file_path)
                            for _ in range(node.level):
                                current_dir = os.path.dirname(current_dir)
                            if node.modname:
                                import_path = os.path.join(current_dir, *node.modname.split('.'))
                            else:
                                import_path = current_dir
                            print("\033[94mRelative import: {} -> {} -> {}\033[0m".format(file_path, node.modname, import_path))
                        else:  # Handle absolute imports
                            if node.modname:
                                import_path = resolve_import(node.modname, file_path, repo_path)
                                print("\033[92mAbsolute import: {} -> {} -> {}\033[0m".format(file_path, node.modname, import_path))
                        # Resolve import path and add edge to graph
                        if import_path:
                            print("_" * 100)
                            print("\033[92mImport path: {}\033[0m".format(import_path))
                            print("_" * 100)
                            G.add_edge(relative_path, import_path, type="import_from")
            except Exception as e:
                import traceback
                traceback.print_exc()
                logging.error("Error parsing Python file {}: {}".format(file_path, e))
        
        # For JavaScript/TypeScript files
        elif file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            analyze_js_ts_with_regex(file_path, repo_path, G)
    
    except Exception as e:
        logging.error("Error processing file {}: {}".format(file_path, e))

