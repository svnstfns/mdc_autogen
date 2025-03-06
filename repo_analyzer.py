import os
import json
import re
import argparse
import asyncio
import shutil
import traceback
import fnmatch
import ast
import astroid
from astroid import nodes
import networkx as nx
from collections import defaultdict
from git import Repo
import logging
from openai import AsyncOpenAI
from instructor import from_openai
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize OpenAI client with instructor
client = from_openai(AsyncOpenAI())


class ChatResponse(BaseModel):
    summary: str = Field(..., description="A summary of the coding function, class, or free text.")


# ===== REPOSITORY STRUCTURE ANALYSIS =====


def glob_to_regex(pattern):
    """Convert a glob pattern to a regular expression."""
    return re.compile(fnmatch.translate(pattern))


def get_ignore_patterns(local_path):
    """Get compiled ignore patterns from .gitignore and common patterns."""
    # Read .gitignore file
    gitignore_path = os.path.join(local_path, ".gitignore")
    ignore_patterns = []
    gitignore_exists = False
    
    if os.path.exists(gitignore_path):
        gitignore_exists = True
        with open(gitignore_path, "r") as f:
            ignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        logging.info(f"Found .gitignore file with {len(ignore_patterns)} patterns")
    
    # Precompile regex patterns for efficiency
    compiled_ignore_patterns = [glob_to_regex(pattern) for pattern in ignore_patterns]

    # Only use common patterns if no .gitignore was found
    if not gitignore_exists:
        logging.info("No .gitignore file found, using default ignore patterns")
        # Common patterns to ignore
        common_ignores = [
            r".*\.git/.*",
            r".*\.github/.*",
            r".*__init__.py",
            r".*package-lock.json",
            r".*package.json",
            r".*\.DS_Store",
            r".*\.vscode/.*",
            r".*tests/.*",
            r".*\.pyc",
            r".*__pycache__/.*",
            r".*\.idea/.*",
            r".*\.env",
            r".*node_modules/.*",  # Ignore node_modules directories
            r".*dist/.*",  # Ignore distribution directories
            r".*build/.*",  # Ignore build directories
            r".*vendor/.*",  # Ignore vendor directories
            r".*\.next/.*",  # Ignore Next.js build output
            r".*coverage/.*",  # Ignore test coverage reports
            r".*__pycache__",
            r".*\.pytest_cache/.*",
            r".*\.cache/.*",
        ]
        
        for pattern in common_ignores:
            compiled_ignore_patterns.append(re.compile(pattern))
        
    return compiled_ignore_patterns


def should_ignore(file_path, compiled_ignore_patterns):
    """Check if a file path should be ignored based on patterns."""
    try:
        # Convert file_path to an absolute path for consistent matching
        abs_file_path = os.path.abspath(file_path)
        for pattern in compiled_ignore_patterns:
            if pattern.match(abs_file_path):
                return True
    except Exception as e:
        logging.error(f"Error checking ignore pattern: {e}. File path: {file_path}")
    return False


def get_repo_files(repo_url=None, local_path=None, oauth_token=None):
    """
    Get a list of relevant files from a repository.
    
    Args:
        repo_url: GitHub repository URL (optional if local_path is a valid repo)
        local_path: Local path to repository
        oauth_token: OAuth token for private repositories
        
    Returns:
        List of relevant files
    """
    # Check if we need to clone the repository
    if repo_url and not os.path.exists(local_path):
        logging.info(f"Cloning repository: {repo_url}")
        
        # Handle OAuth token for private repositories
        if oauth_token:
            # Format the URL with the token for authentication
            if repo_url.startswith("https://"):
                auth_url = repo_url.replace("https://", f"https://{oauth_token}:x-oauth-basic@")
                Repo.clone_from(auth_url, local_path)
            else:
                logging.error("OAuth token provided but repository URL is not HTTPS")
                return []
        else:
            # Clone public repository
            Repo.clone_from(repo_url, local_path)
    elif os.path.exists(local_path):
        logging.info(f"Using existing repository at {local_path}")
    else:
        logging.error("Neither a valid repository URL nor a local path was provided")
        return []

    # Get ignore patterns
    compiled_ignore_patterns = get_ignore_patterns(local_path)

    # Collect all relevant files
    relevant_files = []
    for root, dirs, files in os.walk(local_path):
        # Filter out directories that match ignore patterns
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), compiled_ignore_patterns)]

        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, local_path)
            if not should_ignore(file_path, compiled_ignore_patterns):
                relevant_files.append(rel_path)

    return relevant_files


def generate_directory_structure(repo_path):
    """Generate a visual representation of the repository directory structure."""
    result = []
    
    # Get ignore patterns
    compiled_ignore_patterns = get_ignore_patterns(repo_path)

    def _list_directory(path, prefix="", is_last=False):
        rel_path = os.path.relpath(path, repo_path)

        # Skip paths that should be ignored
        if should_ignore(path, compiled_ignore_patterns):
            return

        # Use appropriate branch symbols
        branch = "└── " if is_last else "├── "
        result.append(f"{prefix}{branch}{os.path.basename(path)}")

        # Prepare the prefix for children
        extension = "    " if is_last else "│   "

        # List directories first, then files
        items = os.listdir(path)
        dirs = sorted([item for item in items if os.path.isdir(os.path.join(path, item)) and not should_ignore(os.path.join(path, item), compiled_ignore_patterns)])
        files = sorted([item for item in items if os.path.isfile(os.path.join(path, item)) and not should_ignore(os.path.join(path, item), compiled_ignore_patterns)])

        # Process directories
        for i, d in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and not files
            _list_directory(os.path.join(path, d), prefix + extension, is_last_dir)

        # Process files
        for i, f in enumerate(files):
            is_last_file = i == len(files) - 1
            branch = "└── " if is_last_file else "├── "
            result.append(f"{prefix}{extension}{branch}{f}")

    # Start from the root directory
    result.append(os.path.basename(repo_path) + "/")
    _list_directory(repo_path)

    return "\n".join(result)


# ===== SYMBOLIC GRAPH ANALYSIS =====


def preprocess_content(content):
    """Preprocess Python content to handle potential syntax issues."""
    preprocessed_lines = []
    for line in content.splitlines():
        if not line.strip().startswith("python"):
            preprocessed_lines.append(line)
    return "\n".join(preprocessed_lines)


def analyze_sys_path_modifications(content):
    """Analyze sys.path modifications in the Python code."""
    preprocessed_content = preprocess_content(content)
    try:
        tree = ast.parse(preprocessed_content)
    except SyntaxError as e:
        logging.error(f"Failed to parse content due to a syntax error: {e}")
        return []

    sys_path_mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                    if target.value.id == "sys" and target.attr == "path":
                        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                            if node.value.func.attr in ["append", "insert"]:
                                sys_path_mods.append((node.value.func.attr, node.value.args[0]))
    return sys_path_mods


def apply_sys_path_modifications(base_path, sys_path_mods, repo_path):
    """Apply sys.path modifications for import resolution."""
    modified_sys_path = [repo_path]  # Start with the repo path
    for mod in sys_path_mods:
        if isinstance(mod[1], ast.Str):
            path = mod[1].s
            if not os.path.isabs(path):
                path = os.path.abspath(os.path.join(os.path.dirname(base_path), path))
            if mod[0] == "append":
                modified_sys_path.append(path)
            elif mod[0] == "insert":
                modified_sys_path.insert(0, path)
    return modified_sys_path


def resolve_import(import_name, current_file, repo_path):
    """Attempt to resolve an import to an actual file in the repository."""
    parts = import_name.split(".")
    for i in range(len(parts), 0, -1):
        potential_path = os.path.join(repo_path, *parts[:i])
        if os.path.isfile(potential_path + ".py"):
            return os.path.relpath(potential_path + ".py", repo_path)
        if os.path.isdir(potential_path) and os.path.isfile(os.path.join(potential_path, "__init__.py")):
            return os.path.relpath(os.path.join(potential_path, "__init__.py"), repo_path)
    return None


def analyze_imports_and_usage(file_path, repo_path, G):
    """Analyze imports and function/class usage in a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Analyze sys.path modifications
        try:
            sys_path_mods = analyze_sys_path_modifications(content)
            modified_sys_path = apply_sys_path_modifications(file_path, sys_path_mods, repo_path)
        except Exception as e:
            logging.error(f"Error analyzing sys.path modifications in {file_path}: {e}")
            sys_path_mods = []
            modified_sys_path = [repo_path]

        relative_path = os.path.relpath(file_path, repo_path)
        G.add_node(relative_path, type="file")

        try:
            # Try parsing with astroid first
            module = astroid.parse(content, module_name=file_path)
            use_astroid = True
        except astroid.exceptions.AstroidSyntaxError:
            # If astroid fails, fall back to the built-in ast module
            logging.warning(f"Astroid failed to parse {file_path}. Falling back to ast.")
            module = ast.parse(content)
            use_astroid = False

        imports = set()
        function_calls = set()
        defined_functions = set()
        defined_classes = set()
        method_calls = set()

        def process_node(node, parent=None):
            nonlocal imports, function_calls, defined_functions, defined_classes, method_calls

            if use_astroid:
                if isinstance(node, nodes.Import):
                    for name in node.names:
                        resolved = resolve_import(name[0], file_path, repo_path)
                        if resolved:
                            imports.add(resolved)
                            G.add_edge(relative_path, resolved, type="import")

                elif isinstance(node, nodes.ImportFrom):
                    if node.level == 0:  # absolute import
                        full_name = f"{node.modname}.{node.names[0][0]}" if node.modname else node.names[0][0]
                    else:  # relative import
                        parts = os.path.dirname(file_path).split(os.sep)
                        full_name = ".".join(parts[-(node.level - 1) :] + [node.modname] + [node.names[0][0]])
                    resolved = resolve_import(full_name, file_path, repo_path)
                    if resolved:
                        imports.add(resolved)
                        G.add_edge(relative_path, resolved, type="import")

                elif isinstance(node, nodes.FunctionDef):
                    func_name = f"{relative_path}:{node.name}"
                    defined_functions.add(func_name)
                    G.add_node(func_name, type="function")
                    G.add_edge(relative_path, func_name, type="defines")
                    if parent and isinstance(parent, nodes.ClassDef):
                        G.add_edge(f"{relative_path}:{parent.name}", func_name, type="method")

                elif isinstance(node, nodes.ClassDef):
                    class_name = f"{relative_path}:{node.name}"
                    defined_classes.add(class_name)
                    G.add_node(class_name, type="class")
                    G.add_edge(relative_path, class_name, type="defines")

                elif isinstance(node, nodes.Call):
                    if isinstance(node.func, nodes.Name):
                        function_calls.add(node.func.name)
                        G.add_edge(relative_path, node.func.name, type="calls")
                    elif isinstance(node.func, nodes.Attribute):
                        full_call = f"{node.func.expr.as_string()}.{node.func.attrname}"
                        method_calls.add(full_call)
                        G.add_edge(relative_path, full_call, type="calls")
            else:
                # ast-specific parsing (simpler, less detailed)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        resolved = resolve_import(alias.name, file_path, repo_path)
                        if resolved:
                            imports.add(resolved)
                            G.add_edge(relative_path, resolved, type="import")

                elif isinstance(node, ast.ImportFrom):
                    module = node.module if node.module else ""
                    for alias in node.names:
                        full_name = f"{module}.{alias.name}" if module else alias.name
                        resolved = resolve_import(full_name, file_path, repo_path)
                        if resolved:
                            imports.add(resolved)
                            G.add_edge(relative_path, resolved, type="import")

                elif isinstance(node, ast.FunctionDef):
                    func_name = f"{relative_path}:{node.name}"
                    defined_functions.add(func_name)
                    G.add_node(func_name, type="function")
                    G.add_edge(relative_path, func_name, type="defines")

                elif isinstance(node, ast.ClassDef):
                    class_name = f"{relative_path}:{node.name}"
                    defined_classes.add(class_name)
                    G.add_node(class_name, type="class")
                    G.add_edge(relative_path, class_name, type="defines")

                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        function_calls.add(node.func.id)
                        G.add_edge(relative_path, node.func.id, type="calls")
                    elif isinstance(node.func, ast.Attribute):
                        try:
                            value_str = ast.unparse(node.func.value)
                            full_call = f"{value_str}.{node.func.attr}"
                            method_calls.add(full_call)
                            G.add_edge(relative_path, full_call, type="calls")
                        except (AttributeError, ValueError):
                            # ast.unparse is Python 3.9+, handle older versions
                            pass

            # Process all child nodes
            if use_astroid:
                for child in node.get_children():
                    process_node(child, node)
            else:
                for child in ast.iter_child_nodes(node):
                    process_node(child, node)

        process_node(module)

        # Link method calls to their definitions if possible
        for call in method_calls:
            if "." in call:
                parts = call.split(".")
                class_name, method_name = parts[0], parts[-1]
                potential_method = f"{relative_path}:{class_name}.{method_name}"
                if potential_method in defined_functions:
                    G.add_edge(relative_path, potential_method, type="calls")

        # Link function calls to their definitions if possible
        for call in function_calls:
            potential_function = f"{relative_path}:{call}"
            if potential_function in defined_functions:
                G.add_edge(relative_path, potential_function, type="calls")
            else:
                # Check if it's an imported function
                for imp in imports:
                    if G.has_node(f"{imp}:{call}"):
                        G.add_edge(relative_path, f"{imp}:{call}", type="calls")
                        break

    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
        traceback.print_exc()


def export_graph_visualization(G, output_file):
    """Create a visualization of the graph and save it to a file."""
    # Save the graph in multiple formats for different use cases
    nx.write_graphml(G, f"{output_file}.graphml")

    # Create a simplified JSON representation for easy parsing
    graph_data = {"nodes": [], "edges": []}

    for node, attrs in G.nodes(data=True):
        graph_data["nodes"].append({"id": node, "type": attrs.get("type", "unknown")})

    for source, target, attrs in G.edges(data=True):
        graph_data["edges"].append({"source": source, "target": target, "type": attrs.get("type", "unknown")})

    with open(f"{output_file}.json", "w") as f:
        json.dump(graph_data, f, indent=2)

    logging.info(f"Graph saved to {output_file}.graphml and {output_file}.json")


# ===== CODE SUMMARIZATION =====


def read_file_content(file_path):
    """Read the content of a file with proper encoding handling."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with another encoding if utf-8 fails
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()


def split_content(content, file_path):
    """Split Python file content into functions, classes, and free-standing code."""
    # Handle Python files
    if file_path.endswith(".py"):
        try:
            module = astroid.parse(content)
            splits = []
            current_block = []

            for node in module.body:
                if isinstance(node, (nodes.FunctionDef, nodes.ClassDef)):
                    if current_block:
                        splits.append({"name": "free_standing_code", "type": "code", "content": "\n".join(current_block)})
                        current_block = []
                    splits.append({"name": node.name, "type": type(node).__name__, "content": node.as_string()})
                else:
                    current_block.append(node.as_string())

            if current_block:
                splits.append({"name": "free_standing_code", "type": "code", "content": "\n".join(current_block)})
            return splits if splits else [{"name": "whole_file", "type": "file", "content": content}]
        except Exception:
            # If parsing fails, return the whole content
            return [{"name": "whole_file", "type": "file", "content": content}]
    # Handle JavaScript and TypeScript files
    elif file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
        # For now, we'll just treat JS/TS files as whole files
        # In a more advanced implementation, you could use a JS/TS parser
        return [{"name": "whole_file", "type": "javascript_or_typescript", "content": content}]
    else:
        # For all other file types, just include them as whole files
        return [{"name": "whole_file", "type": "file", "content": content}]


async def get_chat_openai(prompt, model_name="gpt-4o-mini", **kwargs):
    """Call OpenAI API to get a summary of the code."""
    temperature = kwargs.get("temperature", 0.0)
    max_tokens = kwargs.get("max_tokens", 2000)
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert code analyzer. Make sure to provide a detailed summary of the provided code."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_model=ChatResponse,
        )
        return response
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return ChatResponse(summary=f"An error occurred while processing the request: {str(e)}")


async def generate_summaries(file_data):
    """Generate summaries for all code snippets in the repository."""
    tasks = []
    summaries = defaultdict(list)

    # Prepare all the API requests
    for file_path, snippets in file_data.items():
        for snippet in snippets:
            prompt = (
                f"Filename: {file_path}\n__________________________\n\nCode snippet ({snippet['name']}, {snippet['type']}):\n\n{snippet['content']}"
            )
            task = get_chat_openai(prompt)
            tasks.append((file_path, snippet["name"], snippet["type"], task))

    # Process the API requests in parallel
    logging.info(f"Generating summaries for {len(tasks)} code snippets...")
    for file_path, name, type_info, task in tasks:
        try:
            response = await task
            summaries[file_path].append({"name": name, "type": type_info, "summary": response.summary})
        except Exception as e:
            logging.error(f"Error generating summary for {file_path} - {name}: {e}")
            summaries[file_path].append({"name": name, "type": type_info, "summary": f"Error generating summary: {str(e)}"})

    return summaries


# ===== MAIN FUNCTIONS =====


async def analyze_repository(repo_url=None, local_path=None, output_dir="output", oauth_token=None):
    """
    Analyze a repository and generate structure, graph, and summaries.
    
    Supports Python, JavaScript, and TypeScript files. Python files will have
    detailed AST-based analysis of functions, classes, and dependencies, while
    JavaScript and TypeScript files are included with basic information.
    
    Args:
        repo_url: GitHub repository URL (optional if local_path is provided)
        local_path: Local path to repository (optional if repo_url is provided)
        output_dir: Directory to save output files
        oauth_token: OAuth token for private repositories
    """
    # Set default local path if not provided
    if not local_path:
        local_path = './temp_repo'
        should_cleanup = True
    else:
        # If using an existing local repo, don't clean it up
        should_cleanup = False
    
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Get repository files and ignore patterns
        logging.info("Collecting repository files...")
        relevant_files = get_repo_files(repo_url, local_path, oauth_token)
        compiled_ignore_patterns = get_ignore_patterns(local_path)
        logging.info(f"Found {len(relevant_files)} relevant files")
        
        # Step 2: Generate directory structure
        logging.info("Generating directory structure visualization...")
        structure = generate_directory_structure(local_path)
        with open(os.path.join(output_dir, "directory_structure.txt"), 'w') as f:
            f.write(structure)
        logging.info("Directory structure visualization saved to directory_structure.txt")
        
        # Step 3: Create symbolic graph
        logging.info("Analyzing code structure and dependencies...")
        G = nx.DiGraph()
        for file_path in relevant_files:
            full_path = os.path.join(local_path, file_path)
            
            # Process Python files with AST-based analysis
            if file_path.endswith('.py'):
                analyze_imports_and_usage(full_path, local_path, G)
            # Add nodes for JavaScript and TypeScript files without detailed analysis
            elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                relative_path = os.path.relpath(full_path, local_path)
                G.add_node(relative_path, type="file")
                # In the future, we could implement a JS/TS-specific analyzer here
        
        # Export the graph
        export_graph_visualization(G, os.path.join(output_dir, "repo_graph"))
        
        # Step 4: Split files and prepare for summarization
        logging.info("Splitting files into functions and classes...")
        file_data = {}
        for file_path in relevant_files:
            full_path = os.path.join(local_path, file_path)
            try:
                content = read_file_content(full_path)
                file_data[file_path] = split_content(content, file_path)
            except Exception as e:
                logging.error(f"Error processing file: {file_path}. Error: {e}")
        
        exit()
        # Step 5: Generate summaries
        logging.info("Generating code summaries...")
        summaries = await generate_summaries(file_data)
        
        # Save the summaries
        with open(os.path.join(output_dir, "summaries.json"), 'w', encoding='utf-8') as f:
            json.dump(summaries, f, indent=2, ensure_ascii=False)
        logging.info("Code summaries saved to summaries.json")
        
        # Create a combined report
        logging.info("Creating combined analysis report...")
        with open(os.path.join(output_dir, "repo_analysis_report.md"), 'w') as f:
            # Write header
            f.write("# Repository Analysis Report\n\n")
            
            # Include repo info
            if repo_url:
                f.write(f"## Repository: {repo_url}\n\n")
            else:
                f.write(f"## Local Repository: {os.path.abspath(local_path)}\n\n")
            
            # Include directory structure
            f.write("## Directory Structure\n\n")
            f.write("```\n")
            f.write(structure)
            f.write("\n```\n\n")
            
            # Include graph summary
            f.write("## Code Dependency Graph\n\n")
            f.write(f"- Total files analyzed: {len(G.nodes())}\n")
            f.write(f"- Total relationships: {len(G.edges())}\n\n")
            f.write("See repo_graph.graphml and repo_graph.json for detailed graph data.\n\n")
            
            # Include code summaries
            f.write("## Code Summaries\n\n")
            for file_path, file_summaries in summaries.items():
                f.write(f"### {file_path}\n\n")
                for item in file_summaries:
                    f.write(f"#### {item['name']} ({item['type']})\n\n")
                    f.write(f"{item['summary']}\n\n")
            
            logging.info("Analysis report saved to repo_analysis_report.md")
        
        return os.path.abspath(output_dir)
        
    except Exception as e:
        logging.error(f"Error analyzing repository: {e}")
        traceback.print_exc()
        return None
    finally:
        # Clean up: remove the temporary repository only if we created it
        if should_cleanup:
            logging.info("Cleaning up temporary files...")
            shutil.rmtree(local_path, ignore_errors=True)


def main():
    """Main function to parse arguments and run the analysis."""
    parser = argparse.ArgumentParser(description="Analyze a repository with support for Python, JavaScript, and TypeScript")
    parser.add_argument("--repo_url", help="GitHub repository URL (optional if --local_path is provided)")
    parser.add_argument("--local_path", help="Local path to repository (optional if --repo_url is provided)")
    parser.add_argument("--output_dir", default="output", help="Output directory for analysis files")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use for summaries")
    parser.add_argument("--oauth_token", help="OAuth token for private repositories")
    args = parser.parse_args()
    
    # Validate arguments
    if not args.repo_url and not args.local_path:
        logging.error("Error: Either --repo_url or --local_path must be provided")
        return
    
    # Set the OpenAI API key from environment
    if not os.environ.get("OPENAI_API_KEY"):
        logging.error("Error: OPENAI_API_KEY environment variable not set. Required for code summarization.")
        return
    
    # Run the analysis
    output_path = asyncio.run(analyze_repository(
        repo_url=args.repo_url,
        local_path=args.local_path,
        output_dir=args.output_dir,
        oauth_token=args.oauth_token
    ))
    
    if output_path:
        logging.info(f"Repository analysis complete! Results saved to {output_path}")
    else:
        logging.error("Repository analysis failed.")


if __name__ == "__main__":
    main()
