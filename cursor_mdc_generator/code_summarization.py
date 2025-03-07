import astroid
from astroid import nodes
import logging
import os
from openai import AsyncOpenAI
from instructor import from_openai
from pydantic import BaseModel, Field
import networkx as nx


class MDCResponse(BaseModel):
    """Model for structured MDC file content generation."""
    description: str = Field(
        ...,
        description="A brief description of what this rule provides context for."
    )
    globs: list[str] = Field(
        ...,
        description="File patterns this rule applies to, using glob syntax."
    )
    always_apply: bool = Field(
        default=False,
        description="Whether this rule should always be applied regardless of file context."
    )
    content: str = Field(
        ...,
        description="The markdown content providing useful documentation and context."
    )


client = from_openai(AsyncOpenAI())


def read_file_content(file_path):
    """Read the content of a file with proper encoding handling."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        try:
            # Try with another encoding if utf-8 fails
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception:
            logging.error(f"Error reading file {file_path}: {e}")
            return None


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
        pass
    else:
        # For all other file types, just include them as whole files
        return [{"name": "whole_file", "type": "file", "content": content}]


async def generate_mdc_file(
    file_path, 
    file_snippets, 
    dependency_graph, 
    output_dir, 
    model_name="gpt-4o-mini", 
    temperature=0.3
):
    """
    Generate an MDC file for a specific file, including dependency information.
    
    Args:
        file_path: Path to the file to document
        file_snippets: Dictionary of code snippets for this file
        dependency_graph: NetworkX DiGraph with dependency information
        output_dir: Directory to write the MDC file
        model_name: OpenAI model to use
        temperature: Temperature for generation
        
    Returns:
        Path to the generated MDC file
    """
    try:
        # Create file-specific MDC path
        mdc_path = os.path.join(output_dir, f"{file_path}.mdc")
        os.makedirs(os.path.dirname(mdc_path), exist_ok=True)
        
        # Get dependency information
        imported_by = []
        imports = []
        
        if file_path in dependency_graph.nodes():
            # Files that import this file
            imported_by = [pred for pred in dependency_graph.predecessors(file_path)]
            # Files that this file imports
            imports = [succ for succ in dependency_graph.successors(file_path)]
        
        # Build the prompt with file content and dependencies
        prompt = f"""
You are creating contextual documentation for a file in a codebase: {file_path}

Here is the content of the file broken down into components:

"""
        for snippet in file_snippets:
            prompt += f"\n## {snippet['name']} ({snippet['type']})\n"
            prompt += f"```python\n{snippet['content']}\n```\n"
        
        # Add dependency information
        prompt += "\n## Dependency Information\n"
        
        if imports:
            prompt += "\nThis file imports the following files:\n"
            for imp in imports:
                prompt += f"- {imp}\n"
        else:
            prompt += "\nThis file does not import any other files in the repository.\n"
            
        if imported_by:
            prompt += "\nThis file is imported by the following files:\n"
            for imp_by in imported_by:
                prompt += f"- {imp_by}\n"
        else:
            prompt += "\nThis file is not imported by any other files in the repository.\n"
        
        prompt += f"""
Based on the file content and dependency information, create a .mdc file for Cursor IDE with:

1. A concise description field explaining what this file does
2. Appropriate glob patterns (use: {file_path})
3. Whether this rule should always apply (typically false)
4. Detailed markdown content with:
   - Overview of the file's purpose and functionality
   - Description of key components (functions, classes, etc.)
   - How this file relates to other files in the codebase (dependencies)
   - Usage examples where appropriate
   - Best practices when working with this code

The output should help developers quickly understand this file and its role in the larger codebase.
"""

        # Generate MDC content
        response = await client.chat.completions.create(
            model=model_name,
            response_model=MDCResponse,
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert code documentation specialist."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        
        # Write MDC file
        write_mdc_file(mdc_path, response)
        return mdc_path
    
    except Exception as e:
        logging.error(f"Error generating MDC for {file_path}: {e}")
        return None


async def generate_directory_mdc(
    directory, 
    file_snippets_dict, 
    dependency_graph, 
    output_dir, 
    model_name="gpt-4o-mini", 
    temperature=0.3
):
    """
    Generate an MDC file for a directory, including dependency information.
    
    Args:
        directory: Directory path to document
        file_snippets_dict: Dictionary of code snippets for files in this directory
        dependency_graph: NetworkX DiGraph with dependency information
        output_dir: Directory to write the MDC file
        model_name: OpenAI model to use
        temperature: Temperature for generation
        
    Returns:
        Path to the generated MDC file
    """
    try:
        # Create directory-specific MDC path
        dir_mdc_path = os.path.join(output_dir, directory, "_directory.mdc")
        os.makedirs(os.path.dirname(dir_mdc_path), exist_ok=True)
        
        # Find files in this directory
        dir_files = [f for f in file_snippets_dict.keys() if os.path.dirname(f) == directory]
        
        # Get dependency information for the directory as a whole
        dir_imports = set()
        imported_by_dir = set()
        
        for file_path in dir_files:
            if file_path in dependency_graph.nodes():
                # Files outside this directory that are imported by files in this directory
                dir_imports.update([
                    succ for succ in dependency_graph.successors(file_path)
                    if os.path.dirname(succ) != directory
                ])
                
                # Files outside this directory that import files in this directory
                imported_by_dir.update([
                    pred for pred in dependency_graph.predecessors(file_path)
                    if os.path.dirname(pred) != directory
                ])
        
        # Build the prompt
        prompt = f"""
You are creating contextual documentation for a directory in a codebase: {directory}

This directory contains the following files:
"""
        for file_path in dir_files:
            prompt += f"- {os.path.basename(file_path)}\n"
        
        # Add dependency information
        prompt += "\n## External Dependencies\n"
        
        if dir_imports:
            prompt += "\nFiles in this directory import from these external locations:\n"
            for imp in dir_imports:
                prompt += f"- {imp}\n"
        else:
            prompt += "\nThis directory doesn't import from any external files.\n"
            
        if imported_by_dir:
            prompt += "\nFiles in this directory are imported by these external locations:\n"
            for imp_by in imported_by_dir:
                prompt += f"- {imp_by}\n"
        else:
            prompt += "\nNo external files import from this directory.\n"
        
        prompt += f"""
Based on the directory content and dependency information, create a .mdc file for Cursor IDE with:

1. A concise description field explaining what this directory contains
2. Appropriate glob patterns (use: {directory}/*)
3. Whether this rule should always apply (typically false)
4. Detailed markdown content with:
   - Overview of the directory's purpose
   - Summary of key files and their roles
   - How this directory relates to other parts of the codebase
   - Common patterns or conventions used
   - Best practices when working with files in this directory

The output should help developers quickly understand the purpose and organization of this directory.
"""

        # Generate MDC content
        response = await client.chat.completions.create(
            model=model_name,
            response_model=MDCResponse,
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert code documentation specialist."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        
        # Write MDC file
        write_mdc_file(dir_mdc_path, response)
        return dir_mdc_path
    
    except Exception as e:
        logging.error(f"Error generating directory MDC for {directory}: {e}")
        return None


async def generate_high_level_mdc(
    repo_path, 
    file_snippets_dict, 
    dependency_graph, 
    output_dir, 
    model_name="gpt-4o-mini", 
    temperature=0.3
):
    """
    Generate a high-level MDC file for the entire repository.
    
    Args:
        repo_path: Path to the repository
        file_snippets_dict: Dictionary of code snippets for all files
        dependency_graph: NetworkX DiGraph with dependency information
        output_dir: Directory to write the MDC file
        model_name: OpenAI model to use
        temperature: Temperature for generation
        
    Returns:
        Path to the generated MDC file
    """
    try:
        # Create repository-level MDC path
        repo_mdc_path = os.path.join(output_dir, "_repository.mdc")
        os.makedirs(os.path.dirname(repo_mdc_path), exist_ok=True)
        
        # Get top-level directories
        directories = {os.path.dirname(f) for f in file_snippets_dict.keys() if os.path.dirname(f)}
        
        # Analyze core modules (most imported files)
        in_degree = sorted([(n, dependency_graph.in_degree(n)) for n in dependency_graph.nodes()], 
                          key=lambda x: x[1], reverse=True)
        core_modules = [n for n, d in in_degree if d >= 3]  # Files imported by at least 3 other files
        
        # Build the prompt
        prompt = f"""
You are creating high-level documentation for an entire repository.

The repository contains the following directories:
"""
        for directory in sorted(directories):
            prompt += f"- {directory}\n"
        
        # Add dependency information
        prompt += "\n## Core Modules\n"
        
        if core_modules:
            prompt += "\nThese files are imported by multiple other files and represent core functionality:\n"
            for module in core_modules[:10]:  # Show top 10
                prompt += f"- {module} (imported by {dependency_graph.in_degree(module)} files)\n"
        
        # Try to identify entry points
        entry_points = [n for n in dependency_graph.nodes() 
                       if dependency_graph.out_degree(n) > 0 and dependency_graph.in_degree(n) == 0]
        
        if entry_points:
            prompt += "\n## Entry Points\n"
            prompt += "\nThese files import other modules but are not imported themselves:\n"
            for entry in entry_points:
                prompt += f"- {entry}\n"
        
        # Identify circular dependencies
        try:
            cycles = list(nx.simple_cycles(dependency_graph))
            if cycles:
                prompt += "\n## Circular Dependencies\n"
                prompt += "\nThe following circular dependencies were detected:\n"
                for i, cycle in enumerate(cycles[:5]):  # Show at most 5 cycles
                    prompt += f"{i+1}. Cycle: {' → '.join(cycle)} → {cycle[0]}\n"
        except Exception:
            pass
        
        prompt += f"""
Based on the repository structure and dependency information, create a .mdc file for Cursor IDE with:

1. A concise description field explaining what this repository does
2. Appropriate glob patterns (use: *)
3. Whether this rule should always apply (typically true for repository-wide documentation)
4. Detailed markdown content with:
   - Overview of the repository's purpose
   - Summary of key directories and their roles
   - Architectural patterns and organization
   - Core modules and their significance
   - Entry points and how to navigate the codebase
   - Best practices for working with this repository

The output should help developers quickly understand the overall structure and organization of the codebase.
"""

        # Generate MDC content
        response = await client.chat.completions.create(
            model=model_name,
            response_model=MDCResponse,
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert code documentation specialist."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        
        # Write MDC file
        write_mdc_file(repo_mdc_path, response)
        return repo_mdc_path
    
    except Exception as e:
        logging.error(f"Error generating repository MDC: {e}")
        return None


def write_mdc_file(output_path, mdc_content):
    """
    Write the MDC content to a file.
    
    Args:
        output_path: Path to write the MDC file
        mdc_content: MDCResponse object with the content
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write the frontmatter
            f.write("---\n")
            f.write(f"description: {mdc_content.description}\n")
            f.write(f"globs: {mdc_content.globs}\n")
            f.write(f"alwaysApply: {str(mdc_content.always_apply).lower()}\n")
            f.write("---\n\n")
            
            # Write the content
            f.write(mdc_content.content)
        
        logging.info(f"MDC file created: {output_path}")
    except Exception as e:
        logging.error(f"Error writing MDC file {output_path}: {e}")


async def generate_mdc_files(file_data, dependency_graph, output_dir="output/.cursor/rules", model_name="gpt-4o-mini"):
    """
    Generate MDC files for all files, directories, and the repository.
    
    Args:
        file_data: Dictionary of file snippets
        dependency_graph: NetworkX DiGraph with dependency information
        output_dir: Directory to write the MDC files
        model_name: OpenAI model to use
        
    Returns:
        List of paths to generated MDC files
    """
    mdc_files = []
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate file-specific MDCs
    for file_path, snippets in file_data.items():
        if snippets:  # Only generate for files with content
            mdc_path = await generate_mdc_file(
                file_path, 
                snippets, 
                dependency_graph, 
                output_dir, 
                model_name
            )
            if mdc_path:
                mdc_files.append(mdc_path)
    
    # Generate directory MDCs
    directories = {os.path.dirname(f) for f in file_data.keys() if os.path.dirname(f)}
    for directory in directories:
        mdc_path = await generate_directory_mdc(
            directory, 
            file_data, 
            dependency_graph, 
            output_dir, 
            model_name
        )
        if mdc_path:
            mdc_files.append(mdc_path)
    
    # Generate high-level repository MDC
    repo_mdc_path = await generate_high_level_mdc(
        os.path.dirname(list(file_data.keys())[0]) if file_data else ".",
        file_data, 
        dependency_graph, 
        output_dir, 
        model_name
    )
    if repo_mdc_path:
        mdc_files.append(repo_mdc_path)
    
    return mdc_files
