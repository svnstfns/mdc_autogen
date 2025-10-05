# Cursor Rules Repository Analysis

## MDC format with frontmatter structure

The MDC (Markdown Cursor) format has emerged as the standard for organizing cursor rules across repositories, providing intelligent rule activation and cross-tool compatibility. Based on the analysis of sparesparrow/cursor-rules, the format follows a precise structure that enables sophisticated rule management.

### Core MDC file structure

Every `.mdc` file follows this exact pattern:

```yaml
---
description: Brief description of the rule's purpose
globs: ["pattern/to/match/*.{ts,js}"]
alwaysApply: false
priority: 10
dependencies: ["other-rule.mdc"]
---

# Rule Title

## Core Principles
...

## Code Standards
...

## Validation Rules
...
```

The **frontmatter fields** serve specific purposes:
- **description**: Used by AI agents to determine when to apply the rule automatically
- **globs**: File patterns for automatic rule attachment (e.g., `"src/**/*.ts"`, `"*.component.tsx"`)
- **alwaysApply**: Boolean controlling whether rule applies to every interaction
- **priority**: Numeric value for rule precedence when multiple rules match
- **dependencies**: Array of other .mdc files this rule depends on

### Four distinct rule types

The frontmatter configuration determines rule behavior, creating four distinct types:

**Always Rules** (`-always.mdc`): Applied to every chat and command execution with empty description and globs, but `alwaysApply: true`.

**Auto-Attach Rules** (`-auto.mdc`): Triggered when current file matches glob patterns, with required glob patterns and `alwaysApply: false`.

**Agent Selected Rules** (`-agent.mdc`): AI agent decides application based on comprehensive description, with empty globs and `alwaysApply: false`.

**Manual Rules** (`-manual.mdc`): Must be explicitly referenced with @ command, all fields empty or false except basic metadata.

## Sparesparrow's organizational structure

The sparesparrow repository demonstrates the most sophisticated organizational approach with a hierarchical folder structure within `.cursor/rules/`:

```
.cursor/rules/
├── core/                    # Foundational rules
│   ├── base-agentic.mdc    # Agentic workflow patterns
│   └── base-devops.mdc     # AI-driven DevOps standards
├── framework/               # Framework-specific rules
│   ├── typescript.mdc      # TypeScript standards
│   └── mcp-typescript.mdc  # MCP-specific standards
├── domain/                  # Domain-specific rules
│   ├── composer-agent.mdc          
│   ├── cognitive-architecture.mdc  
│   └── solid-analyzer.mdc         
├── security/               # Security rules
│   └── security.mdc       
└── patterns/              # Advanced patterns
    └── top5-inspirations.mdc
```

**Naming conventions** follow kebab-case with descriptive suffixes: `base-agentic.mdc`, `composer-agent-instructions.mdc`. Optional suffixes indicate rule type: `-auto.mdc`, `-agent.mdc`, `-always.mdc`, `-manual.mdc`.

## Best practices across repositories

### PatrickJS's categorization system

PatrickJS/awesome-cursorrules employs a **10-category system** for organizing rules by technology domain:

1. Frontend Frameworks and Libraries
2. Backend and Full-Stack
3. Mobile Development
4. CSS and Styling
5. State Management
6. Database and API
7. Testing
8. Build Tools and Development
9. Language-Specific
10. Other

Files follow the pattern `technology-focus-cursorrules-prompt-file` (e.g., `nextjs-tailwind-typescript-cursorrules-prompt-file`), emphasizing **integration-focused rules** that combine multiple technologies for real-world scenarios.

### Steipete's cross-tool compatibility

The steipete/agent-rules repository innovates with **unified .mdc format** that works across different AI assistants. Cursor reads the YAML frontmatter for intelligent rule application, while Claude Code processes the markdown content, ignoring metadata. This approach ensures **single source of truth** for rules across multiple tools.

The repository also demonstrates **MCP (Model Context Protocol) integration** for extended AI capabilities, including screenshot capture with AI analysis, GitHub repository management, and persistent knowledge storage.

### Blefnk's numbering system

Blefnk/awesome-cursor-rules uses a **structured numbering format** for categorical organization:
- 100-199: Basic/foundational rules
- 200-299: Framework-specific rules
- 300-399: Testing and quality assurance
- 2000+: Advanced framework rules

This system enables **quick identification** of rule categories and maintains clear hierarchy. The repository also provides a **CLI tool** (`@reliverse/cli`) for automated rule installation.

## Modern web development rules

### Framework-specific patterns

**Next.js 15 with App Router** rules emphasize React Server Components by default, explicit `'use client'` directives only for interactivity, server actions for forms instead of traditional API routes, and URL search params for shareable state management.

**React 19 patterns** focus on functional components with proper TypeScript typing, hooks composition for logic reuse, suspense boundaries for loading states, and error boundaries for graceful degradation.

**TypeScript 5 standards** include strict mode compilation, interfaces over types for extensibility, comprehensive type coverage without `any`, and proper generic constraints.

### Testing and quality assurance

Modern testing rules prioritize **Vitest for unit testing** with clear describe blocks, atomic assertions, and descriptive test names. **Playwright for E2E testing** covers user journeys, accessibility checks, and visual regression testing. **Component testing** uses Testing Library patterns with user-centric queries and interaction testing.

### Development workflow rules

**Commit conventions** follow conventional commit format with semantic versioning support and automated changelog generation. **Code review patterns** include multi-perspective analysis, performance impact assessment, and security vulnerability checks. **Documentation standards** require inline JSDoc comments, README maintenance, and API documentation updates.

## Practical implementation patterns

### Glob pattern usage

Effective glob patterns enable precise rule targeting:
- All TypeScript files: `"**/*.ts"`
- React components only: `"**/*.component.tsx"`
- Test files: `"**/*.{test,spec}.ts"`
- Specific directories: `"src/features/**/*.ts"`
- Multiple extensions: `"**/*.{js,jsx,ts,tsx}"`

### Rule composition with dependencies

Complex behaviors emerge from **rule composition**:

```yaml
---
description: "Advanced React component standards"
globs: ["src/components/**/*.tsx"]
dependencies: ["core/typescript.mdc", "framework/react-base.mdc"]
---
```

This allows **modular rule design** where base rules provide foundation and specialized rules extend functionality without duplication.

### Context-aware activation

Rules activate based on **multiple signals**: file type matching via globs, AI assessment of task relevance, explicit user invocation, and project configuration. This creates an **intelligent assistance layer** that provides relevant guidance without overwhelming developers.

## Key insights for implementation

The analysis reveals that successful cursor rule systems share several characteristics. They maintain **focused, single-purpose rules** under 50 lines for clarity. They include **both valid and invalid examples** to demonstrate proper usage. They use **clear, actionable language** avoiding ambiguity. They organize rules in **logical categories** matching mental models. They avoid **rule duplication** through dependencies and composition.

For modern web development projects, the most valuable approach combines sparesparrow's hierarchical organization for scalability, PatrickJS's technology categorization for discoverability, steipete's cross-tool compatibility for flexibility, and blefnk's numbering system for maintainability.

The MDC format with proper frontmatter enables **sophisticated rule management** while maintaining **simplicity for basic use cases**. This balance between power and usability makes it the recommended standard for cursor rule implementation in modern development workflows.