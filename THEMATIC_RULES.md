# Thematic Rule Generation

This document describes the thematic rule generation system for Cursor MDC rules.

## Overview

The thematic rule generation system is a new approach to generating Cursor IDE documentation rules. Instead of creating one rule per file (which can lead to rule flooding), it detects project properties (frameworks, tooling, configs) and plans targeted rule-sets based on what's actually in your project.

## Key Differences from File-Based Generation

| Feature | File-Based (`mdcgen`) | Thematic (`mdcgen-thematic`) |
|---------|----------------------|------------------------------|
| **Scope** | Individual files | Project-wide themes |
| **Output** | One MDC per file | Rule-sets for detected technologies |
| **Use Case** | Detailed file documentation | Framework/tooling best practices |
| **Detection** | N/A | Automatic technology detection |
| **Planning** | File-by-file | Technology-driven |

Both CLIs can coexist and serve different purposes. Use thematic for initial project setup and framework-level rules, then use file-based for detailed file-specific documentation.

## Components

### 1. Rule Planner (`rule_planner.py`)

Detects project properties and plans thematic rules:

- **ProjectDetector**: Scans configuration files and project structure to detect technologies
  - Frontend frameworks (Vue, React)
  - Backend frameworks (FastAPI, Flask, Django)
  - Languages (Python, TypeScript, JavaScript)
  - Databases (SQLite, PostgreSQL, SQLAlchemy)
  - Testing tools (pytest, Jest, Vitest)
  - Build/lint/format tools (Vite, Ruff, Black, ESLint, Prettier)
  - Infrastructure (Docker, Kubernetes)

- **ThematicRulePlanner**: Plans rule-sets based on detections
  - Maps detected technologies to appropriate rules
  - Avoids duplication across categories
  - Provides project context for LLM prompts

### 2. Rule ID Allocator (`rule_id_allocator.py`)

Manages unique rule IDs within category ranges:

- Scans existing rules to track used IDs
- Allocates next available ID in category range
- Prevents ID conflicts
- Provides category statistics

**ID Ranges:**

| Category | Range | Purpose |
|----------|-------|---------|
| `00-foundation` | 100-199 | Project-wide standards, governance |
| `01-frontend` | 200-299 | UI frameworks, components |
| `02-backend` | 300-399 | API servers, routing |
| `03-mobile` | 400-499 | Mobile-specific development |
| `04-css` | 500-599 | Styling, design systems |
| `05-state` | 600-699 | State management |
| `06-db-api` | 700-799 | Databases, API contracts |
| `07-testing` | 800-899 | Testing frameworks, strategies |
| `08-build-dev` | 900-999 | Build tools, dev workflow |
| `09-language` | 1000-1099 | Language-specific standards |
| `99-other` | 9000-9999 | Miscellaneous |

### 3. Rule Authoring Specification (`rule_authoring_spec.md`)

Defines quality standards for rules:

- **Frontmatter requirements**: description, globs, alwaysApply, category, rule_id, tags
- **Activation types**: Always, Auto, Agent, Manual
- **Content standards**: Structure, examples, requirements
- **Quality checklist**: What makes a good rule
- **LLM generation guidance**: How to prompt for quality output

This specification is provided to the LLM before each rule generation to ensure consistent quality.

### 4. Mapping Configuration (`data/mapping.yaml`)

Maps detected technologies to rule specifications:

```yaml
detections:
  vue:
    - category: "01-frontend"
      slug: "vue-component-architecture"
      description: "Standards for Vue component architecture"
      tags: ["vue", "components", "architecture"]
      globs: ["**/*.vue"]
      activation: "auto"
```

The mapping can be customized per project. The system works without PyYAML (falls back to JSON if needed).

### 5. Thematic CLI (`cli_thematic.py`)

Separate CLI that doesn't interfere with existing file-based CLI:

```bash
# Basic usage
python -m cursor_mdc_generator.cli_thematic --repo . --output-dir .

# With custom configuration
python -m cursor_mdc_generator.cli_thematic \
    --repo /path/to/project \
    --mapping custom_mapping.yaml \
    --spec custom_authoring_spec.md \
    --model gpt-4o \
    --output-dir /path/to/output

# Skip ID assignment for review
python -m cursor_mdc_generator.cli_thematic --repo . --no-assign-ids
```

Or use the installed command:

```bash
mdcgen-thematic --repo . --output-dir .
```

### 6. Enhanced LLM Prompts

New prompts in `llm_utils/prompts.py`:

- **`format_thematic_rule_prompt`**: Generates rules following authoring spec
  - Includes project context
  - References authoring standards
  - Requests specific, actionable content
  
- **`format_project_summary_prompt`**: Creates high-level project overview
  - Foundation-level rule
  - Technology stack summary
  - Getting started guide

## Usage

### Prerequisites

1. **Install the package:**
   ```bash
   pip install mdcgen
   ```

2. **Set API key:**
   ```bash
   export OPENAI_API_KEY="sk-..."
   # or ANTHROPIC_API_KEY, GEMINI_API_KEY
   ```

### Generate Rules

```bash
# Navigate to your project
cd /path/to/your/project

# Generate thematic rules
mdcgen-thematic --repo . --output-dir .
```

This will:
1. Detect technologies in your project
2. Plan appropriate rule-sets
3. Generate rules using LLM
4. Assign unique IDs
5. Create `.cursor/rules/` directory structure
6. Update `INDEX.md`

### Review Output

Generated rules appear in:

```
.cursor/rules/
├── 00-foundation/
│   └── 100-base-standards.mdc
├── 01-frontend/
│   └── 200-vue-component-architecture.mdc
├── 02-backend/
│   └── 301-fastapi-routing-structure.mdc
├── 07-testing/
│   └── 801-pytest-structure-coverage.mdc
├── 08-build-dev/
│   └── 900-precommit-ruff-black.mdc
└── INDEX.md
```

### Customization

#### Custom Mapping

Create a custom mapping file for project-specific needs:

```yaml
# my-mapping.yaml
detections:
  custom-framework:
    - category: "02-backend"
      slug: "custom-framework-patterns"
      description: "Patterns for our custom framework"
      tags: ["custom", "backend"]
      globs: ["**/*.custom"]
      activation: "auto"
```

Use it:
```bash
mdcgen-thematic --mapping my-mapping.yaml
```

#### Custom Authoring Spec

Modify `rule_authoring_spec.md` or create your own:

```bash
mdcgen-thematic --spec my-custom-spec.md
```

#### Different Models

Use different LLM models:

```bash
mdcgen-thematic --model gpt-4o-mini  # Faster, cheaper
mdcgen-thematic --model gpt-4o       # Higher quality
mdcgen-thematic --model claude-3-opus  # Alternative provider
```

## Integration with Cursor Agent

The example rule at `examples/.cursor/rules/00-foundation/120-agent-exec-thematic.mdc` shows how to integrate with Cursor Agent:

1. Agent can execute the CLI with proper environment handling
2. No need to extract keys from desktop apps
3. Use ENV variables (OPENAI_API_KEY, etc.)
4. Automated workflow: detect → plan → generate → review

## Robustness & Fallbacks

### YAML Dependency

The system works without PyYAML:
- Tries to load YAML first (if PyYAML installed)
- Falls back to JSON if YAML not available
- Provides clear error messages

### Error Handling

- Missing API keys: Clear error message with instructions
- ID range exhaustion: Suggests consolidation or custom ranges
- Module not found: Points to installation instructions
- LLM failures: Logs errors and continues with other rules

### Safe Defaults

- Default mapping included in package
- Authoring spec embedded in package
- Sensible ID ranges defined
- Foundation rules always included

## Best Practices

1. **Run from project root**: Ensures accurate detection
2. **Review before committing**: Always check generated rules
3. **Use --no-assign-ids first**: Review content, then regenerate with IDs
4. **Custom mapping for specialized projects**: Tailor to your needs
5. **Version control mapping and rules**: Track evolution over time

## Security

- **Never commit API keys**: Use environment variables
- **Use .env files**: For local development (add to .gitignore)
- **Rotate keys regularly**: Security best practice
- **Limit key permissions**: Only what's needed

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Generate Cursor Rules
on:
  push:
    branches: [main]

jobs:
  generate-rules:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install mdcgen
        run: pip install mdcgen
      
      - name: Generate Rules
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          mdcgen-thematic --repo . --output-dir .
      
      - name: Commit Rules
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add .cursor/rules/
          git commit -m "Update Cursor rules" || echo "No changes"
          git push
```

## Troubleshooting

### No rules generated

**Cause**: Project technologies not detected or not in mapping

**Solution**: 
1. Check detection: Add logging with `--log-level DEBUG`
2. Review/customize mapping.yaml
3. Verify config files are present (package.json, pyproject.toml, etc.)

### Rule quality issues

**Cause**: LLM not following spec, vague prompts

**Solution**:
1. Use higher quality model (gpt-4o instead of gpt-4o-mini)
2. Review/enhance rule_authoring_spec.md
3. Provide more project context in mapping descriptions

### ID conflicts

**Cause**: Manual rules created with same IDs

**Solution**:
1. Use RuleIDAllocator when creating manual rules
2. Check existing IDs before assignment
3. Use category stats to see availability

## Future Enhancements

Potential improvements:
- Interactive mode for rule selection
- Dry-run mode to preview without generating
- Rule quality scoring post-generation
- Template-based generation for common patterns
- Integration with existing MDC quality checker
- Automatic rule updates when dependencies change

## Related Documentation

- [Rule Authoring Specification](cursor_mdc_generator/rule_authoring_spec.md) - Quality standards
- [Example Agent Rule](examples/.cursor/rules/00-foundation/120-agent-exec-thematic.mdc) - Integration guide
- [Cursor Rules Knowledge](cursor-rules-current-en/knowldege-mdc-rules.md) - Best practices from community

## Support

For issues or questions:
- Check this documentation first
- Review example rules in `examples/`
- Check logs with `--log-level DEBUG`
- Review generated rules and mapping
- Open an issue on GitHub
