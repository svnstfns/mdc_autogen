# Cursor MDC Generator

A tool to generate Cursor IDE documentation files (MDC) from repository analysis.

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

macOS:
```bash
brew install graphviz
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
# Analyze a local repository
mdcgen analyze --local /path/to/repository

# Analyze a remote repository
mdcgen analyze --repo https://github.com/user/repo

# Specify output directory
mdcgen analyze --repo https://github.com/user/repo --out ./mdc-output

# Use a specific model
mdcgen analyze --local /path/to/repo --model gpt-4o

# Skip visualization (useful if you don't have Graphviz installed)
mdcgen analyze --local /path/to/repo --no-viz
```

For private repositories:

```bash
mdcgen analyze --repo https://github.com/user/private-repo --token YOUR_GITHUB_TOKEN
```

## Features

- Analyzes repository structure and code dependencies
- Creates dependency graphs to visualize relationships between files (if enabled)
- Generates documentation files (MDC) for use with Cursor IDE
- Supports both local and remote repositories
- Compatible with various programming languages (python, typescript, javascript for now)

## Requirements

- Python 3.7+
- OpenAI/Anthropic/Google Key (set as environment variable vis-a-vis LiteLLM format)

## Command Reference

| Option | Alias | Description |
|--------|-------|-------------|
| `--repo` | `-r` | GitHub repository URL |
| `--local` | `-l` | Local path to repository |
| `--out` | `-o` | Output directory for analysis files |
| `--model` | `-m` | Model to use for summaries (default: gpt-4o-mini) |
| `--token` | `-t` | OAuth token for private repositories |
| `--imports` | `-i` | Include @file references to imported files |
| `--no-viz` | | Skip generating dependency graph visualizations |
| `--no-dirs` | | Skip generating directory-level MDC files |
| `--depth` | `-d` | Max directory depth (0=repo only, 1=top-level dirs) |
| `--log-level` | | Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

# Skip all directory-level MDCs (only generate file and repository MDCs)
mdcgen analyze --local /path/to/repo --no-dirs

# Limit directory depth (0=repo only, 1=top-level dirs only)
mdcgen analyze --local /path/to/repo --depth 1

# Include import references in MDC files
mdcgen analyze --local /path/to/repo --imports

# Using short aliases for common options
mdcgen analyze -l /path/to/repo -o ./output -m gpt-4o -d 1
