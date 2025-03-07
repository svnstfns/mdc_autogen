import os
import re
import astroid
from astroid import nodes
import logging
import networkx as nx

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def is_standard_library(module_name):
    """Check if a module is part of the Python standard library."""
    # List of common standard library modules
    stdlib_modules = {
        "abc",
        "argparse",
        "ast",
        "asyncio",
        "base64",
        "collections",
        "contextlib",
        "copy",
        "csv",
        "datetime",
        "enum",
        "functools",
        "glob",
        "gzip",
        "hashlib",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "os",
        "pathlib",
        "pickle",
        "random",
        "re",
        "shutil",
        "socket",
        "sqlite3",
        "string",
        "struct",
        "subprocess",
        "sys",
        "tempfile",
        "threading",
        "time",
        "traceback",
        "typing",
        "unittest",
        "urllib",
        "uuid",
        "xml",
        "zipfile",
    }

    # Check if it's a direct standard library module
    if module_name in stdlib_modules:
        return True

    # Check if it's a submodule of a standard library module
    main_module = module_name.split(".")[0]
    return main_module in stdlib_modules


def resolve_import(import_name, current_file, repo_path):
    """
    Resolve an import statement to a file path.

    Args:
        import_name: The name of the imported module
        current_file: The file containing the import
        repo_path: The root path of the repository

    Returns:
        The absolute file path of the imported module, or None if not found
    """
    try:
        # Handle standard library imports
        if is_standard_library(import_name.split(".")[0]):
            return None

        # Try direct absolute path first
        potential_paths = []

        # Basic path (assuming import_name maps directly to file structure)
        base_path = os.path.join(repo_path, import_name.replace(".", "/"))
        potential_paths.append(f"{base_path}.py")
        potential_paths.append(os.path.join(base_path, "__init__.py"))

        # Handle imports that might be relative to different project roots
        # This helps with imports like 'src.schemas.user'
        if current_file:
            # Get possible project roots by looking at parent directories
            possible_roots = []

            # Add the current repo_path
            possible_roots.append(repo_path)

            # Add the directory containing the importing file
            file_dir = os.path.dirname(current_file)
            possible_roots.append(file_dir)

            # Add possible project roots by going up the directory tree
            current_dir = file_dir
            for _ in range(5):  # Try up to 5 levels up
                current_dir = os.path.dirname(current_dir)
                possible_roots.append(current_dir)

                # Check for common project indicators
                if (
                    os.path.exists(os.path.join(current_dir, "setup.py"))
                    or os.path.exists(os.path.join(current_dir, "pyproject.toml"))
                    or os.path.exists(os.path.join(current_dir, "requirements.txt"))
                ):
                    # This might be a project root, prioritize it
                    possible_roots.insert(0, current_dir)

            # For each possible root, try to resolve the import
            for root in possible_roots:
                # Try direct module path
                module_path = os.path.join(root, import_name.replace(".", "/"))
                potential_paths.append(f"{module_path}.py")
                potential_paths.append(os.path.join(module_path, "__init__.py"))

                # Try first part as a top-level package
                parts = import_name.split(".")
                if len(parts) > 1:
                    # Check if the first part exists as a directory
                    first_part_dir = os.path.join(root, parts[0])
                    if os.path.isdir(first_part_dir):
                        # Try the rest of the import path
                        rest_path = "/".join(parts[1:])
                        potential_paths.append(
                            os.path.join(first_part_dir, f"{rest_path}.py")
                        )
                        potential_paths.append(
                            os.path.join(first_part_dir, rest_path, "__init__.py")
                        )

        # Handle relative imports
        if current_file and import_name.startswith("."):
            current_dir = os.path.dirname(current_file)

            # For each relative level (e.g., .. or ...), go up one directory
            relative_level = 0
            module_name = import_name
            while module_name.startswith("."):
                relative_level += 1
                module_name = module_name[1:]

            # Go up relative_level directories from current_dir
            relative_dir = current_dir
            for _ in range(relative_level):
                relative_dir = os.path.dirname(relative_dir)

            if module_name:  # If there's a module specified after the dots
                rel_path = os.path.join(relative_dir, module_name.replace(".", "/"))
                potential_paths.append(f"{rel_path}.py")
                potential_paths.append(os.path.join(rel_path, "__init__.py"))
            else:  # If import is just dots (like 'from .. import x')
                potential_paths.append(f"{relative_dir}.py")
                potential_paths.append(os.path.join(relative_dir, "__init__.py"))

        # Try to find the file in potential locations (remove duplicates)
        checked_paths = set()
        for path in potential_paths:
            if path in checked_paths:
                continue
            checked_paths.add(path)

            # Normalize path for comparison
            norm_path = os.path.normpath(path)
            if os.path.isfile(norm_path):
                return norm_path

        # If we get here, we haven't found a specific Python file
        # Try checking for directories
        for path in potential_paths:
            dir_path = path.replace(".py", "")
            if os.path.isdir(dir_path) and os.path.exists(
                os.path.join(dir_path, "__init__.py")
            ):
                return os.path.join(dir_path, "__init__.py")

        # Check if the import is a namespace package without __init__.py
        base_path = os.path.join(repo_path, import_name.replace(".", "/"))
        if os.path.isdir(base_path):
            # Look for any Python files in this directory
            for file in os.listdir(base_path):
                if file.endswith(".py"):
                    return base_path

        # For absolute imports like 'src.schemas.user', try to find the module at the repo root
        # This handles projects with non-standard layouts
        if "." in import_name:
            # Split the import into parts
            parts = import_name.split(".")

            # Try different combinations of the parts as project roots
            for i in range(1, len(parts)):
                # Try using first i parts as the project structure
                base_dir = os.path.join(repo_path, *parts[:i])
                if os.path.isdir(base_dir):
                    # Try resolving the rest of the import from this directory
                    remaining = parts[i:]
                    if remaining:
                        submodule_path = os.path.join(base_dir, *remaining)
                        if os.path.isfile(f"{submodule_path}.py"):
                            return f"{submodule_path}.py"
                        if os.path.isdir(submodule_path) and os.path.isfile(
                            os.path.join(submodule_path, "__init__.py")
                        ):
                            return os.path.join(submodule_path, "__init__.py")

        # If not found in repo, log and try Python's import system
        logging.debug(f"Could not resolve import: {import_name} from {current_file}")
        return None

    except Exception as e:
        logging.debug(f"Error resolving import {import_name}: {e}")
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

    # Use absolute path instead of relative path
    # relative_path = os.path.relpath(file_path, repo_path)

    # Add node for this file if it doesn't exist
    if file_path not in G.nodes():
        G.add_node(file_path, type="file")

    # Regex patterns to match different types of imports with capturing groups for imported items
    simple_import_patterns = [
        # CommonJS require: const x = require('path')
        r"(?:const|let|var)\s+(\w+)\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]",
        # Dynamic imports: import('path')
        r"import\s*\(\s*['\"]([^'\"]+)['\"]",
        # Add pattern for CSS/SCSS imports
        r"@import\s+['\"]([^'\"]+)['\"]",
        # Add pattern for image/asset imports
        r"(?:src|href|url)\s*=\s*['\"]([^'\"]+\.(?:png|jpg|jpeg|gif|svg|webp|ico))['\"]",
    ]

    # ES6 named imports: import { X, Y as Z } from 'path'
    es6_named_import_pattern = r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]"

    # ES6 default import: import X from 'path'
    es6_default_import_pattern = r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]"

    # ES6 namespace import: import * as X from 'path'
    es6_namespace_import_pattern = (
        r"import\s+\*\s+as\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]"
    )

    # Process simple imports
    imports_with_sources = []
    for pattern in simple_import_patterns:
        matches = re.findall(pattern, content)
        if matches:
            for match in matches:
                if len(match) == 2:  # Variable name and path
                    var_name, path = match
                    imports_with_sources.append(
                        (path, [{"name": var_name, "alias": None, "type": "module"}])
                    )
                else:  # Only path
                    imports_with_sources.append(
                        (match, [{"name": "*", "alias": None, "type": "module"}])
                    )

    # Process ES6 named imports
    for match in re.finditer(es6_named_import_pattern, content):
        import_names_str = match.group(1)
        path = match.group(2)

        imported_items = []
        for import_item in import_names_str.split(","):
            import_item = import_item.strip()
            if "as" in import_item:
                name, alias = [x.strip() for x in import_item.split("as")]
                imported_items.append({"name": name, "alias": alias, "type": "unknown"})
            else:
                imported_items.append(
                    {"name": import_item, "alias": None, "type": "unknown"}
                )

        imports_with_sources.append((path, imported_items))

    # Process ES6 default imports
    for match in re.finditer(es6_default_import_pattern, content):
        var_name = match.group(1)
        path = match.group(2)
        imported_items = [{"name": "default", "alias": var_name, "type": "default"}]
        imports_with_sources.append((path, imported_items))

    # Process ES6 namespace imports
    for match in re.finditer(es6_namespace_import_pattern, content):
        var_name = match.group(1)
        path = match.group(2)
        imported_items = [{"name": "*", "alias": var_name, "type": "namespace"}]
        imports_with_sources.append((path, imported_items))

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
                if (
                    "compilerOptions" in tsconfig
                    and "paths" in tsconfig["compilerOptions"]
                ):
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

    # Process all imports and add edges to the graph
    for imported_path, imported_items in imports_with_sources:
        # Skip absolute URLs
        if imported_path.startswith(("http://", "https://", "//")):
            continue

        # Skip built-in modules and third-party packages
        if not imported_path.startswith((".", "/")) and not os.path.isabs(
            imported_path
        ):
            # This is likely a third-party package
            continue

        # Handle path aliases
        found = False
        for alias, target in aliases.items():
            if imported_path.startswith(alias):
                aliased_path = imported_path.replace(alias, target)
                # Try to find a file with this path
                potential_target = os.path.join(repo_path, aliased_path)

                # Try different extensions
                for ext in ["", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"]:
                    target_with_ext = potential_target + ext
                    if os.path.exists(target_with_ext):
                        target = os.path.relpath(target_with_ext, repo_path)
                        target_full_path = os.path.abspath(
                            target_with_ext
                        )  # Get absolute path
                        if target_full_path not in G.nodes():
                            G.add_node(target_full_path, type="file")

                        # Add edge with imported items
                        if G.has_edge(file_path, target_full_path):
                            G[file_path][target_full_path]["imported_items"].extend(
                                imported_items
                            )
                        else:
                            G.add_edge(
                                file_path,
                                target_full_path,
                                type="js_import",
                                imported_items=imported_items,
                            )

                        found = True
                        break

                if found:
                    break

        if found:
            continue

        # Try to resolve the path
        base_dir = os.path.dirname(file_path)
        if imported_path.startswith("."):
            # Relative import
            target_path = os.path.normpath(os.path.join(base_dir, imported_path))
        elif imported_path.startswith("/"):
            # Absolute import relative to repo root
            target_path = os.path.normpath(
                os.path.join(repo_path, imported_path.lstrip("/"))
            )
        else:
            # Skip node_modules imports
            continue

        # Try different extensions
        for ext in ["", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"]:
            target_with_ext = target_path + ext
            if os.path.exists(target_with_ext):
                target = os.path.relpath(target_with_ext, repo_path)
                target_full_path = os.path.abspath(target_with_ext)  # Get absolute path
                if target_full_path not in G.nodes():
                    G.add_node(target_full_path, type="file")

                # Add edge with imported items
                if G.has_edge(file_path, target_full_path):
                    G[file_path][target_full_path]["imported_items"].extend(
                        imported_items
                    )
                else:
                    G.add_edge(
                        file_path,
                        target_full_path,
                        type="js_import",
                        imported_items=imported_items,
                    )

                found = True
                break

        if found:
            continue

        # Check for directory with index file
        for index_file in [
            "index.js",
            "index.jsx",
            "index.ts",
            "index.tsx",
            "index.vue",
            "index.svelte",
        ]:
            index_path = os.path.join(target_path, index_file)
            if os.path.exists(index_path):
                target = os.path.relpath(index_path, repo_path)
                target_full_path = os.path.abspath(index_path)  # Get absolute path
                if target_full_path not in G.nodes():
                    G.add_node(target_full_path, type="file")

                # Add edge with imported items
                if G.has_edge(file_path, target_full_path):
                    G[file_path][target_full_path]["imported_items"].extend(
                        imported_items
                    )
                else:
                    G.add_edge(
                        file_path,
                        target_full_path,
                        type="js_import",
                        imported_items=imported_items,
                    )

                found = True
                break

        # If we still haven't found the file, log it
        if not found:
            logging.debug(
                "Could not resolve JS/TS import: {} from {}".format(
                    imported_path, file_path
                )
            )


def get_imported_item_type(module, item_name):
    """Determine the type of an imported item from a module."""
    try:
        # First check if the item is directly in the module
        if item_name in module.locals:
            node = module.locals[item_name][0]

            # Check node type based on its class
            if isinstance(node, astroid.nodes.ClassDef):
                return "class"
            elif isinstance(node, astroid.nodes.FunctionDef):
                return "function"
            elif isinstance(node, astroid.nodes.AssignName):
                # For variables, check if they're constants
                if item_name.isupper():
                    return "constant"
                return "variable"
            elif isinstance(node, astroid.nodes.ImportFrom) or isinstance(
                node, astroid.nodes.Import
            ):
                return "module"
            else:
                # Try to infer the type from node properties
                try:
                    inferred = next(node.infer())
                    if isinstance(inferred, astroid.nodes.ClassDef):
                        return "class"
                    elif isinstance(inferred, astroid.nodes.FunctionDef):
                        return "function"
                    elif isinstance(inferred, astroid.nodes.Const):
                        return "constant"
                    elif isinstance(inferred, astroid.nodes.Module):
                        return "module"
                except:
                    pass

        # If not found or couldn't determine type, check for submodules
        for submodule_name, submodule in module.items():
            if isinstance(submodule, astroid.nodes.Module):
                if item_name in submodule.locals:
                    return get_imported_item_type(submodule, item_name)

        # If we reach here, we couldn't determine the type
        return "unknown"
    except Exception as e:
        logging.debug(f"Error determining type for {item_name}: {e}")
        return "unknown"


def analyze_imports_and_usage(file_path, repo_path, G):
    """Analyze imports and function/class usage in a Python file."""
    try:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()

        # Add node for this file if it doesn't exist
        if file_path not in G.nodes():
            G.add_node(file_path, type="file")

        # For Python files, use AST to analyze imports
        if file_path.endswith(".py"):
            try:
                # Parse the file with astroid for better import resolution
                module = astroid.parse(content)

                # Process imports and add edges to the graph
                for node in module.body:
                    # Handle regular imports: import foo, bar
                    if isinstance(node, nodes.Import):
                        for name, alias in node.names:
                            # Try to resolve the import to an actual file
                            resolved_path = resolve_import(name, file_path, repo_path)
                            print("\033[93m{} -> {}\033[0m".format(name, resolved_path))
                            if resolved_path:
                                # Make sure the target node exists with type "file"
                                if resolved_path not in G.nodes():
                                    G.add_node(resolved_path, type="file")

                                # For regular imports, the imported name is the module itself
                                imported_items = [
                                    {"name": name, "alias": alias, "type": "module"}
                                ]
                                # Check if edge already exists
                                if G.has_edge(file_path, resolved_path):
                                    # Append to existing imports list
                                    G[file_path][resolved_path][
                                        "imported_items"
                                    ].extend(imported_items)
                                else:
                                    # Create new edge with imports list
                                    G.add_edge(
                                        file_path,
                                        resolved_path,
                                        type="import",
                                        imported_items=imported_items,
                                    )

                    # Handle from imports: from foo import bar, baz
                    elif isinstance(node, nodes.ImportFrom):
                        import_path = None
                        if (
                            node.level and node.level > 0
                        ):  # Handle relative imports, check if level is not None
                            # Calculate the path for relative imports
                            current_dir = os.path.dirname(file_path)
                            for _ in range(
                                node.level - 1
                            ):  # Subtract 1 because first level is the directory containing the file
                                current_dir = os.path.dirname(current_dir)

                            if node.modname:
                                import_path = os.path.join(
                                    current_dir, *node.modname.split(".")
                                )
                            else:
                                import_path = current_dir

                            # Convert to relative path within the repo for the graph
                            if os.path.exists(import_path + ".py"):
                                import_path = import_path + ".py"
                            elif os.path.isdir(import_path) and os.path.exists(
                                os.path.join(import_path, "__init__.py")
                            ):
                                import_path = os.path.join(import_path, "__init__.py")

                            print(
                                "\033[94mRelative import: {} -> {} -> {}\033[0m".format(
                                    file_path, node.modname, import_path
                                )
                            )
                        else:  # Handle absolute imports
                            if node.modname:
                                import_path = resolve_import(
                                    node.modname, file_path, repo_path
                                )
                                print(
                                    "\033[92mAbsolute import: {} -> {} -> {}\033[0m".format(
                                        file_path, node.modname, import_path
                                    )
                                )

                        # Resolve import path and add edge to graph with specific imported items
                        if import_path:
                            # Make sure the target node exists with type "file"
                            if import_path not in G.nodes():
                                G.add_node(import_path, type="file")

                            # Extract the specific names being imported
                            imported_items = []

                            # If possible, try to analyze the target module to determine item types
                            target_types = {}
                            if os.path.isfile(import_path) and import_path.endswith(
                                ".py"
                            ):
                                try:
                                    with open(import_path, "r", encoding="utf-8") as f:
                                        target_content = f.read()
                                    target_module = astroid.parse(target_content)

                                    # Get types for all items in the target module
                                    for item_name, _ in node.names:
                                        if item_name == "*":
                                            print(
                                                "\033[95mWildcard import: {}\033[0m".format(
                                                    item_name
                                                )
                                            )
                                            break
                                        imported_item_type = get_imported_item_type(
                                            target_module, item_name
                                        )
                                        print(
                                            "\033[95mImported item type: {} -> {}\033[0m".format(
                                                item_name, imported_item_type
                                            )
                                        )
                                        target_types[item_name] = imported_item_type
                                except Exception as e:
                                    logging.debug(
                                        "Error analyzing target module {}: {}".format(
                                            import_path, e
                                        )
                                    )

                            for name, alias in node.names:
                                print(
                                    "\033[95mImport name: {} -> {}\033[0m".format(
                                        name, alias
                                    )
                                )
                                # For '*', we indicate it's importing everything
                                if name == "*":
                                    imported_items = [
                                        {"name": "*", "alias": None, "type": "wildcard"}
                                    ]
                                    break
                                else:
                                    # Use the determined type if available, otherwise unknown
                                    item_type = target_types.get(name, "unknown")
                                    print(
                                        "\033[95mImport item type: {} -> {}\033[0m".format(
                                            name, item_type
                                        )
                                    )
                                    imported_items.append(
                                        {
                                            "name": name,
                                            "alias": alias,
                                            "type": item_type,
                                        }
                                    )

                            print("_" * 100)
                            print("\033[92mImport path: {}\033[0m".format(import_path))
                            print(
                                "\033[92mImported items: {}\033[0m".format(
                                    imported_items
                                )
                            )
                            print("_" * 100)
                            # Don't create self-referential edges
                            if file_path != import_path:
                                # Check if edge already exists
                                if G.has_edge(file_path, import_path):
                                    # Append to existing imports list
                                    G[file_path][import_path]["imported_items"].extend(
                                        imported_items
                                    )
                                else:
                                    # Create new edge with imports list
                                    G.add_edge(
                                        file_path,
                                        import_path,
                                        type="import_from",
                                        imported_items=imported_items,
                                    )
                        else:
                            print(
                                "\033[91mCould not resolve import path: {}\033[0m".format(
                                    import_path
                                )
                            )
            except Exception as e:
                import traceback

                traceback.print_exc()
                logging.error("Error parsing Python file {}: {}".format(file_path, e))

        # For JavaScript/TypeScript files
        elif file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            analyze_js_ts_with_regex(file_path, repo_path, G)

    except Exception as e:
        logging.error("Error processing file {}: {}".format(file_path, e))


def convert_to_relative_paths(G, repo_path):
    """
    Convert all absolute paths in the graph to paths relative to the repo_path.

    Args:
        G: The NetworkX graph with absolute paths
        repo_path: The repository root path

    Returns:
        A new graph with relative paths
    """
    # Create a new graph to hold the relative paths
    G_rel = nx.DiGraph()

    # Create a mapping from absolute to relative paths
    node_mapping = {}
    for node in G.nodes():
        # Only process nodes that actually exist and are files/directories
        if isinstance(node, str) and os.path.exists(node):
            try:
                rel_path = os.path.relpath(node, repo_path)
                node_mapping[node] = rel_path
            except ValueError:
                # In case the node is on a different drive than repo_path
                node_mapping[node] = node
        else:
            # For nodes that don't exist or aren't file paths, keep as is
            node_mapping[node] = node

    # Add nodes with relative paths
    for node, data in G.nodes(data=True):
        rel_node = node_mapping.get(node, node)
        G_rel.add_node(rel_node, **data)

    # Add edges with relative paths
    for src, tgt, data in G.edges(data=True):
        rel_src = node_mapping.get(src, src)
        rel_tgt = node_mapping.get(tgt, tgt)
        G_rel.add_edge(rel_src, rel_tgt, **data)

    return G_rel
