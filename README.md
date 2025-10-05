# Cursor MDC Generator

Autogenerate better Cursor documentation files (MDC).
Vibe coding is easier when your AI knows the rules.




## Features

- **Two generation modes**: File-based (detailed docs per file) and Thematic (rule-sets by framework)
- Analyzes repository structure and code dependencies
- **Thematic rule generation** - detects project technologies and generates targeted rule-sets
- Generates documentation files (MDC) for Cursor
- **Intelligent quality assessment** - checks existing MDC files and only updates those with poor quality
- Visualize dependency graph between files (if enabled)
- Supports both local and remote repositories
- Compatible with python, typescript, and javascript (for now)

## How It Works

The MDC generator uses LLMs (Large Language Models) to create contextual documentation. To understand how the LLM knows what structure to use for MDC files, see [LLM_GUIDANCE.md](LLM_GUIDANCE.md) for a detailed explanation of the guidance mechanism.

## Quality Assessment

The tool now includes intelligent quality assessment of existing MDC files. When enabled with `--check-quality` or `--update-poor-quality`, it:

1. **Scans existing MDC files** in `.cursor/rules/` directory
2. **Evaluates quality** based on multiple criteria:
   - **Structure**: Validates frontmatter (description, globs, alwaysApply)
   - **Content Quality**: Checks for meaningful headers, examples, and detailed information
   - **Precision & Focus**: Ensures content is concise, specific, and avoids generic phrases
   - **Completeness**: Detects placeholder content like "TODO" or "TBD"
3. **Generates a report** with quality scores (0-10) and specific issues for each file
4. **Selectively updates** only files that need improvement (with `--update-poor-quality`)

### Quality Metrics

Each MDC file is scored on:
- **Structure (30%)**: Presence and quality of required frontmatter fields
- **Content (40%)**: Depth of documentation, examples, and organization
- **Precision (30%)**: Focus, specificity, and appropriate length

Files scoring **8.0/10 or higher** with at most 1 minor issue are considered high-quality and can be skipped during updates.

### Usage Examples

```bash
# Check quality without regenerating
mdcgen /path/to/repo --check-quality --no-viz

# Only update files with quality issues (smart update)
mdcgen /path/to/repo --update-poor-quality

# Full regeneration (default behavior, no quality check)
mdcgen /path/to/repo
```

The quality report is saved to `mdc_quality_report.md` in your output directory.

## Installation

You can install the package using pip:

```bash
pip install mdcgen
```

Or with uv:

```bash
uv install mdcgen
```

## Installation with Visualization Support

You may need to install pygraphviz separately

macOS:
```bash
brew install graphviz
pip install --global-option=build_ext --global-option="-I/opt/homebrew/include/" --global-option="-L/opt/homebrew/lib/" pygraphviz
pip install mdcgen[visualization]
```

Ubuntu / Debian:
```bash
sudo apt-get install graphviz graphviz-dev
pip install mdcgen[visualization]
```

Windows:
  - Download and install Graphviz from https://graphviz.org/download/
  - Add the Graphviz bin directory to your PATH
  - Run: pip install mdcgen[visualization]

## Usage

### Thematic Rule Generation (Recommended for new projects)

Generate targeted rule-sets based on detected technologies:

```bash
# Generate thematic rules for current project
mdcgen-thematic --repo . --output-dir .

# Use a specific model
mdcgen-thematic --repo . --model gpt-4o

# Skip ID assignment for review first
mdcgen-thematic --repo . --no-assign-ids

# Use custom mapping
mdcgen-thematic --repo . --mapping custom-mapping.yaml
```

See [THEMATIC_RULES.md](THEMATIC_RULES.md) for detailed documentation on thematic rule generation.

### File-Based Documentation

To analyze a repository and generate detailed file-level MDC documentation:

```bash
# Analyze current directory
mdcgen

# Analyze a specific local directory
mdcgen /path/to/repository

# Analyze a remote repository
mdcgen --repo https://github.com/user/repo

# Specify output directory
mdcgen /path/to/repository --out ./mdc-output

# Use a specific model
mdcgen /path/to/repo --model gpt-4o

# Skip visualization (useful if you don't have Graphviz installed)
mdcgen /path/to/repo --no-viz
```

For private repositories:

```bash
mdcgen --repo https://github.com/user/private-repo --token YOUR_GITHUB_TOKEN
```

## Requirements

- Python 3.7+
- OpenAI/Anthropic/Google Key (set as environment variable vis-a-vis LiteLLM format)

## Command Reference

| Option | Alias | Description |
|--------|-------|-------------|
| `PATH` | | Local path to repository (default: current directory) |
| `--repo` | `-r` | GitHub repository URL (instead of local path) |
| `--out` | `-o` | Output directory for analysis files |
| `--model` | `-m` | Model to use for summaries (default: gpt-4o-mini) |
| `--token` | `-t` | OAuth token for private repositories |
| `--imports` | `-i` | Include @file references to imported files |
| `--no-viz` | | Skip generating dependency graph visualizations |
| `--no-dirs` | | Skip generating directory-level MDC files |
| `--depth` | `-d` | Max directory depth (0=repo only, 1=top-level dirs) |
| `--check-quality` | | Check quality of existing MDC files before generating new ones |
| `--update-poor-quality` | | Only update MDC files with poor quality (implies --check-quality) |
| `--log-level` | | Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

## Examples

```bash
# Skip all directory-level MDCs (only generate file and repository MDCs)
mdcgen /path/to/repo --no-dirs

# Limit directory depth (0=repo only, 1=top-level dirs only)
mdcgen /path/to/repo --depth 1

# Include import references in MDC files
mdcgen /path/to/repo --imports

# Check quality of existing MDC files
mdcgen /path/to/repo --check-quality

# Only update MDC files with poor quality (skips high-quality files)
mdcgen /path/to/repo --update-poor-quality

# Using short aliases for common options
mdcgen /path/to/repo -o ./output -m gpt-4o -d 1
```

## How the LLM Creates MDC Files

The tool uses large language models (LLMs) to generate contextual documentation by analyzing your codebase and creating structured MDC files. Here's how it works:

### Structured Output Format

All MDC files follow a structured format defined by the `MDCResponse` model with four key components:

1. **description**: A brief description of what the rule provides context for
2. **globs**: File patterns the rule applies to (using glob syntax)
3. **alwaysApply**: Whether the rule should always be applied (typically `false` except for repository-wide rules)
4. **content**: The markdown content providing useful documentation and context

### Three-Level Documentation Strategy

The tool generates MDC files at three different levels of granularity:

#### 1. File-Level MDC Files

For each file in your codebase, the LLM receives:
- The file's code broken down into components (functions, classes, etc.)
- Files that this file imports
- Files that import this file

The LLM is prompted to create documentation that includes:
- Overview of the file's purpose and functionality
- Description of key components (functions, classes, etc.)
- How the file relates to other files (dependencies)
- Usage examples where appropriate
- Best practices when working with this code

#### 2. Directory-Level MDC Files

For each directory, the LLM receives:
- List of files in the directory
- External files imported by files in this directory
- External files that import from this directory

The LLM is prompted to create documentation that includes:
- Overview of the directory's purpose
- Summary of key files and their roles
- How the directory relates to other parts of the codebase
- Common patterns or conventions used
- Best practices when working with files in this directory

#### 3. Repository-Level MDC File

For the entire repository, the LLM receives:
- List of all directories
- Core modules (files imported by multiple other files)
- Entry points (files that import others but aren't imported themselves)
- Circular dependencies (if any detected)

The LLM is prompted to create documentation that includes:
- Overview of the repository's purpose
- Summary of key directories and their roles
- Architectural patterns and organization
- Core modules and their significance
- Entry points and how to navigate the codebase
- Best practices for working with this repository

### Intelligent Model Selection

The tool automatically selects the most appropriate LLM based on context size:

- **< 128K tokens**: Uses the specified model (default: `gpt-4o-mini`)
- **128K - 200K tokens**: Uses `claude-3-5-sonnet-latest` for larger contexts
- **200K - 1M tokens**: Uses `gemini-2.0-flash` for very large contexts
- **> 1M tokens**: Uses a chunking strategy to process extremely large files

This ensures that even large codebases can be processed efficiently without exceeding model context limits.

### System Prompt

All MDC generation requests use a consistent system prompt:
```
You are an expert code documentation specialist.
```

This establishes the LLM's role and expertise for generating high-quality, developer-focused documentation.
