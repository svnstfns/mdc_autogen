# Rule Authoring Specification

This document defines the standards for creating high-quality Cursor MDC rules.

## Frontmatter Structure

Every MDC rule must begin with YAML frontmatter containing the following fields:

```yaml
---
description: "Brief, clear explanation of what this rule enforces (1-2 sentences)"
globs: ["**/*.py", "**/*.ts"]  # File patterns this rule applies to
alwaysApply: false  # true only for foundation/always-on rules
category: "02-backend"  # Category slug (see ID Ranges below)
rule_id: 301  # Unique ID within category range
tags: ["fastapi", "backend", "routing"]  # Searchable keywords
---
```

### Field Requirements

1. **description**: Required. Must be specific and actionable. Avoid vague phrases like "best practices" without details.

2. **globs**: Required for auto-attach rules, empty array for agent/manual rules. Use specific patterns:
   - Good: `["**/*.vue", "**/*.ts"]`
   - Bad: `["*"]` (too broad)

3. **alwaysApply**: 
   - `true`: Rule applies to every Cursor session (use sparingly, only for foundation rules)
   - `false`: Rule applies based on glob patterns or agent selection (default)

4. **category**: Required. Must match one of the defined categories (see ID Ranges below).

5. **rule_id**: Required. Must be unique and within the category's ID range.

6. **tags**: Required. Minimum 2 tags, help with rule discovery and organization.

## Activation Types

Rules are categorized by how they get activated:

### Always (`-always.mdc`)
- `alwaysApply: true`
- Empty or broad globs
- Applied to every chat and command
- Reserved for critical foundation rules only
- Example: Project-wide coding standards, security basics

### Auto (`-auto.mdc`)
- `alwaysApply: false`
- Specific glob patterns required
- Automatically attached when working in matching files
- Most common type for technology-specific rules
- Example: Vue component standards when editing `.vue` files

### Agent (`-agent.mdc`)
- `alwaysApply: false`
- Empty globs array or very broad patterns
- AI decides when to apply based on comprehensive description
- Used for cross-cutting concerns and architectural patterns
- Example: API design patterns, testing strategies

### Manual (`-manual.mdc`)
- `alwaysApply: false`
- Empty globs array
- Must be explicitly referenced with `@` command
- Used for specialized workflows and documentation
- Example: Deployment procedures, migration guides

## Category ID Ranges

Each category has a designated ID range:

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

## Content Quality Standards

### Structure
- Start with a clear H1 heading matching the rule's purpose
- Use H2 sections for organization: Ziel (Goal), Anforderungen (Requirements), Good/Bad Examples
- Keep rules focused on a single concern (Single Responsibility Principle)
- Target length: 30-100 lines for most rules

### Requirements Section
Must include:
- Specific, actionable points (not vague advice)
- Technical details relevant to the context
- Clear do's and don'ts
- References to relevant documentation when applicable

### Examples
Both Good and Bad examples are strongly recommended:

```markdown
## Good
\`\`\`python
# Correct: Proper type hints and validation
def process_user(user_id: int) -> User:
    if user_id <= 0:
        raise ValueError("Invalid user_id")
    return db.get_user(user_id)
\`\`\`

## Bad
\`\`\`python
# Incorrect: No validation, missing types
def process_user(user_id):
    return db.get_user(user_id)
\`\`\`
```

### Avoid
- Generic advice without specifics ("use best practices")
- Placeholder content (TODO, TBD, etc.)
- Excessive length (>200 lines usually indicates rule should be split)
- Duplicating content from other rules
- Outdated information (always reference current versions)

## File Naming Convention

Rules follow this pattern: `{rule_id}-{slug}.mdc`

Examples:
- `301-fastapi-routing-structure.mdc`
- `205-vue-component-architecture.mdc`
- `801-pytest-structure-coverage.mdc`

The slug should be:
- Kebab-case (lowercase with hyphens)
- Descriptive of the rule's purpose
- Unique within the category
- 2-5 words typically

## Directory Structure

Rules are organized by category:

```
.cursor/rules/
├── 00-foundation/
│   ├── 100-base-standards.mdc
│   └── 120-agent-exec-thematic.mdc
├── 01-frontend/
│   ├── 200-vue-component-architecture.mdc
│   └── 205-react-hooks-patterns.mdc
├── 02-backend/
│   └── 301-fastapi-routing-structure.mdc
└── INDEX.md
```

## Quality Checklist

Before finalizing a rule, verify:

- [ ] Frontmatter is valid YAML with all required fields
- [ ] Rule ID is unique and within category range
- [ ] Description is specific and actionable (not generic)
- [ ] Globs are appropriate for activation type
- [ ] At least 2 meaningful tags are provided
- [ ] Content has clear structure with H1 and H2 headings
- [ ] Both Good and Bad examples are included (when applicable)
- [ ] Requirements are specific and technical
- [ ] No placeholder text (TODO, TBD, etc.)
- [ ] Rule focuses on single concern
- [ ] Length is appropriate (30-100 lines typical)
- [ ] Language is clear and concise
- [ ] Links to documentation are current

## LLM Generation Guidance

When using LLMs to generate rules:

1. **Always provide this specification** as context
2. **Include project-specific context**: detected frameworks, file structure, existing patterns
3. **Request structured output**: Enforce JSON schema or explicit frontmatter format
4. **Validate output**: Check frontmatter, ID ranges, and content quality
5. **Iterate if needed**: Refine vague or generic content
6. **Combine related concepts**: Avoid creating too many narrow rules

Good prompt structure:
```
You are generating a Cursor MDC rule following the Rule Authoring Specification.

Project Context:
- Framework: FastAPI
- Database: SQLAlchemy + SQLite
- Testing: pytest

Create a rule for: "FastAPI routing structure and organization"
Category: 02-backend
Required elements: frontmatter, requirements, good/bad examples

Follow the specification exactly, including proper YAML frontmatter and quality standards.
```

## Maintenance

Rules should be reviewed and updated when:
- Framework versions change significantly
- Project patterns evolve
- Team feedback indicates confusion
- New best practices emerge
- Quality checks reveal issues

Use version control to track rule evolution and maintain history.
