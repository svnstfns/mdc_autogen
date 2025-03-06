# Repository Documentation Generator

This tool generates structured documentation for a repository in the form of `.mdc` files that are compatible with the Cursor IDE's contextual documentation system.

## Overview

The documentation generator consists of two main components:

1. **Repository Analyzer (`repo_analyzer.py`)**: Analyzes a codebase and generates semantic summaries of functions, classes, and files.
2. **MDC File Generator (`generate_mdc_files.py`)**: Creates structured `.mdc` documentation files from the analysis results.

These components are orchestrated by the main script (`generate_docs.py`), which handles the complete workflow from analysis to documentation generation.

## Features

- Generates documentation at multiple levels of abstraction:
  - File-specific (e.g., `src/routers/auth.py.mdc`)
  - Directory-specific (e.g., `src/routers/_directory.mdc`)
  - High-level repository overview (e.g., `_repository.mdc`)
- Structured output in `.mdc` format compatible with Cursor IDE
- Context-aware documentation that understands code structure and semantics
- Documentation is stored in `.cursor/rules/` directory for direct integration with the IDE

## Requirements

- Python 3.8+
- OpenAI API key (set as environment variable `OPENAI_API_KEY`)
- The following Python packages:
  - openai
  - instructor
  - pydantic

Install the required packages with:

```bash
pip install openai instructor pydantic
```

## Usage

### Basic Usage

Run the full documentation generation process with:

```bash
python generate_docs.py --repo_path /path/to/repository
```

By default, the documentation will be stored in the `.cursor/rules/` directory.

### Advanced Options

```bash
python generate_docs.py --repo_path /path/to/repository --output_dir custom/output/path --analysis_dir analysis_results --model gpt-4
```

Parameters:
- `--repo_path`: Path to the repository to analyze (required)
- `--output_dir`: Output directory for MDC files (default: `.cursor/rules`)
- `--analysis_dir`: Directory to store analysis results (default: `analysis_output`)
- `--model`: OpenAI model to use (default: `gpt-4o-mini`)

### Running Individual Components

If you want to run components separately:

1. Run the repository analyzer:
   ```bash
   python repo_analyzer.py --local_path /path/to/repository --output_file summaries.json
   ```

2. Generate MDC files from the analysis:
   ```bash
   python generate_mdc_files.py --repo_path /path/to/repository --summaries_file summaries.json --output_dir .cursor/rules
   ```

## MDC File Format

The `.mdc` files follow this format:

```
---
description: Brief description of what this file/directory contains
globs: src/path/to/file.py  # or src/path/to/directory/*
alwaysApply: false
---

# Detailed Documentation

... Markdown content with comprehensive documentation ...
```

## Integration with Cursor IDE

The generated `.mdc` files are automatically recognized by Cursor IDE when placed in the `.cursor/rules/` directory. When you open a file in the editor, Cursor will display the relevant documentation based on the globs pattern matching.

## License

MIT
