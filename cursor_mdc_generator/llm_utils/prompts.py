import os


def format_file_prompt(file_path, file_snippets, imports, imported_by):
    """Generate the prompt for file-level MDC documentation."""
    prompt = """
You are creating contextual documentation for a file in a codebase: {file_path}

Here is the content of the file broken down into components:

""".format(file_path=file_path)

    for snippet in file_snippets:
        prompt += "\n## {name} ({type})\n".format(
            name=snippet["name"], type=snippet["type"]
        )
        prompt += "```python\n{content}\n```\n".format(content=snippet["content"])

    # Add dependency information
    prompt += "\n## Dependency Information\n"

    if imports:
        prompt += "\nThis file imports the following files:\n"
        for imp in imports:
            prompt += "- {}\n".format(imp)
    else:
        prompt += "\nThis file does not import any other files in the repository.\n"

    if imported_by:
        prompt += "\nThis file is imported by the following files:\n"
        for imp_by in imported_by:
            prompt += "- {}\n".format(imp_by)
    else:
        prompt += "\nThis file is not imported by any other files in the repository.\n"

    prompt += """
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
""".format(file_path=file_path)

    return prompt


def format_directory_prompt(directory, dir_files, dir_imports, imported_by_dir):
    """Generate the prompt for directory-level MDC documentation."""
    prompt = """
You are creating contextual documentation for a directory in a codebase: {directory}

This directory contains the following files:
""".format(directory=directory)

    for file_path in dir_files:
        prompt += "- {}\n".format(os.path.basename(file_path))

    # Add dependency information
    prompt += "\n## External Dependencies\n"

    if dir_imports:
        prompt += "\nFiles in this directory import from these external locations:\n"
        for imp in dir_imports:
            prompt += "- {}\n".format(imp)
    else:
        prompt += "\nThis directory doesn't import from any external files.\n"

    if imported_by_dir:
        prompt += (
            "\nFiles in this directory are imported by these external locations:\n"
        )
        for imp_by in imported_by_dir:
            prompt += "- {}\n".format(imp_by)
    else:
        prompt += "\nNo external files import from this directory.\n"

    prompt += """
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
""".format(directory=directory)

    return prompt


def format_repository_prompt(directories, core_modules, entry_points, cycles=None):
    """Generate the prompt for repository-level MDC documentation."""
    prompt = """
You are creating high-level documentation for an entire repository.

The repository contains the following directories:
"""
    for directory in sorted(directories):
        prompt += "- {}\n".format(directory)

    # Add dependency information
    prompt += "\n## Core Modules\n"

    if core_modules:
        prompt += "\nThese files are imported by multiple other files and represent core functionality:\n"
        for module, in_degree in core_modules[:10]:  # Show top 10
            prompt += "- {} (imported by {} files)\n".format(module, in_degree)

    if entry_points:
        prompt += "\n## Entry Points\n"
        prompt += (
            "\nThese files import other modules but are not imported themselves:\n"
        )
        for entry in entry_points:
            prompt += "- {}\n".format(entry)

    if cycles:
        prompt += "\n## Circular Dependencies\n"
        prompt += "\nThe following circular dependencies were detected:\n"
        for i, cycle in enumerate(cycles[:5]):  # Show at most 5 cycles
            prompt += "{}. Cycle: {} → {}\n".format(i + 1, " → ".join(cycle), cycle[0])

    prompt += """
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

    return prompt


def format_consolidation_prompt(valid_results, mdc_outputs):
    """Format the prompt for consolidating MDC results."""
    prompt = """
    I have processed a large codebase in {} separate chunks, and now I need you to combine these results
    into a single cohesive MDC file. Below are the separate MDC outputs from each chunk:
    
    {}
    
    Please create a single, comprehensive MDC output that synthesizes all the information above, removing duplicates and
    organizing the content logically. The final result should be a cohesive documentation of the entire codebase.
    """.format(len(valid_results), "\n\n".join(mdc_outputs))
    return prompt


# System prompt for all MDC generation requests
SYSTEM_PROMPT = "You are an expert code documentation specialist."


def format_thematic_rule_prompt(
    rule_spec: dict,
    project_context: str,
    authoring_spec: str,
) -> str:
    """
    Generate the prompt for thematic rule generation.

    Args:
        rule_spec: Rule specification with category, slug, description, tags, globs
        project_context: Summary of detected project properties
        authoring_spec: Content of rule_authoring_spec.md

    Returns:
        Formatted prompt for LLM
    """
    prompt = f"""You are generating a high-quality Cursor MDC rule following strict authoring standards.

## Project Context
{project_context}

## Rule Specification to Generate
- **Category**: {rule_spec.get('category', 'unknown')}
- **Slug**: {rule_spec.get('slug', 'unknown')}
- **Description**: {rule_spec.get('description', 'No description provided')}
- **Tags**: {', '.join(rule_spec.get('tags', []))}
- **Glob Patterns**: {', '.join(rule_spec.get('globs', [])) if rule_spec.get('globs') else 'None (agent/manual activation)'}
- **Activation Type**: {rule_spec.get('activation', 'auto')}

## Authoring Standards
{authoring_spec}

## Your Task
Create a complete MDC rule file that:

1. **Follows the frontmatter structure exactly** as specified in the authoring standards
2. **Includes specific, actionable requirements** relevant to the project context
3. **Provides both Good and Bad examples** with actual code snippets
4. **Uses appropriate activation type**:
   - always: alwaysApply=true, empty/broad globs (foundation rules only)
   - auto: alwaysApply=false, specific glob patterns (most common)
   - agent: alwaysApply=false, empty globs, comprehensive description
   - manual: alwaysApply=false, empty globs, minimal description
5. **Maintains focus** on a single concern (30-100 lines typical)
6. **Avoids generic advice** - be specific to {rule_spec.get('slug', 'this topic')}

The rule should be immediately useful to developers working with {project_context.split(':')[0] if ':' in project_context else 'this project'}.

Generate the complete MDC file content including YAML frontmatter and markdown body.
"""
    return prompt


def format_project_summary_prompt(project_context: str) -> str:
    """
    Generate a prompt for creating a project summary rule.

    Args:
        project_context: Summary of detected project properties

    Returns:
        Formatted prompt for LLM
    """
    prompt = f"""You are creating a high-level project overview rule for Cursor IDE.

## Detected Project Properties
{project_context}

## Task
Create a foundation-level MDC rule (00-foundation category) that provides:

1. **Project Overview**: What this project is and its primary purpose
2. **Technology Stack**: Summary of detected frameworks, languages, and tools
3. **Architecture**: High-level organization and key patterns
4. **Development Workflow**: How to build, test, and run the project
5. **Key Directories**: Purpose of main directories
6. **Getting Started**: Quick start guide for new developers

The rule should have:
- Category: 00-foundation
- Slug: project-overview
- alwaysApply: true (this is a foundation rule)
- Empty globs array
- Comprehensive tags

Generate the complete MDC file with YAML frontmatter and detailed markdown content.
"""
    return prompt
