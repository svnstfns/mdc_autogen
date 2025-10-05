# Cursor MDC Generator

Autogenerate better Cursor documentation files (MDC).
Vibe coding is easier when your AI knows the rules.


[![Twitter Follow](https://img.shields.io/twitter/follow/pranaviyer27?style=social)](https://twitter.com/pranaviyer27)

## Features

- Analyzes repository structure and code dependencies
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

To analyze a repository and generate MDC files:

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
