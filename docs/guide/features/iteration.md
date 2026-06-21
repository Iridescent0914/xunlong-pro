# Content Iteration

SmartFin's iteration system allows you to refine and modify generated content without starting from scratch.

## Overview

The Iteration feature:
- 🔄 Modifies existing content intelligently
- 💾 Preserves context and style
- 📝 Targets specific sections or global changes
- 🗂️ Maintains version history
- ⚡ Faster than regeneration

## Quick Start

```bash
# Generate initial content
python SmartFin.py report "AI Trends" --depth standard

# Iterate on it
python SmartFin.py iterate <project-id> "Add more examples in the conclusion"
```

## Modification Scopes

### Local Scope 📍

**Target:** Single section, paragraph, or chapter

**Use cases:**
- Fix typos
- Update specific data
- Rewrite a paragraph
- Add/remove a sentence

**Example:**
```bash
python SmartFin.py iterate <project-id> \
  "Fix the typo in Chapter 3, paragraph 2"
```

**Process:**
```mermaid
graph LR
    A[Identify Section] --> B[Extract Context]
    B --> C[Apply Modification]
    C --> D[Preserve Surrounding Content]
    D --> E[Update Document]
```

**Speed:** ~30 seconds

### Partial Scope 🎯

**Target:** Multiple sections or chapters

**Use cases:**
- Add new sections
- Reorganize chapters
- Expand specific topics
- Remove redundant parts

**Example:**
```bash
python SmartFin.py iterate <project-id> \
  "Add three case studies to chapters 4, 5, and 6"
```

**Process:**
```mermaid
graph LR
    A[Identify Sections] --> B[Plan Changes]
    B --> C[Modify Each Section]
    C --> D[Check Coherence]
    D --> E[Update Document]
```

**Speed:** ~2-5 minutes

### Global Scope 🌐

**Target:** Entire document

**Use cases:**
- Change overall tone
- Add theme throughout
- Restructure document
- Change style/format

**Example:**
```bash
python SmartFin.py iterate <project-id> \
  "Make the entire report more technical and add code examples throughout"
```

**Process:**
```mermaid
graph LR
    A[Analyze Document] --> B[Plan Global Changes]
    B --> C[Regenerate with Context]
    C --> D[Maintain Key Points]
    D --> E[Update Document]
```

**Speed:** ~5-15 minutes

## Common Iteration Tasks

### Adding Content ➕

```bash
# Add new section
python SmartFin.py iterate <project-id> \
  "Add a new section on 'Future Trends' after the current conclusion"

# Add examples
python SmartFin.py iterate <project-id> \
  "Add 2-3 real-world examples to the Implementation section"

# Add data
python SmartFin.py iterate <project-id> \
  "Include recent statistics and market data in Chapter 2"

# Add citations
python SmartFin.py iterate <project-id> \
  "Add more academic citations to support claims in the Literature Review"
```

### Removing Content ➖

```bash
# Remove section
python SmartFin.py iterate <project-id> \
  "Remove the Technical Details section as it's too in-depth"

# Trim content
python SmartFin.py iterate <project-id> \
  "Shorten Chapter 5 by about 30%, focusing on key points only"

# Remove redundancy
python SmartFin.py iterate <project-id> \
  "Remove redundant information between chapters 3 and 7"
```

### Modifying Content ✏️

```bash
# Change tone
python SmartFin.py iterate <project-id> \
  "Make Chapter 4 more casual and conversational"

# Improve clarity
python SmartFin.py iterate <project-id> \
  "Simplify the technical explanations in the Methodology section"

# Enhance detail
python SmartFin.py iterate <project-id> \
  "Expand the character development in chapters 8-10"

# Update information
python SmartFin.py iterate <project-id> \
  "Update the market data with 2025 figures"
```

### Restructuring Content 🔀

```bash
# Reorder sections
python SmartFin.py iterate <project-id> \
  "Move the Case Studies section before the Analysis section"

# Split sections
python SmartFin.py iterate <project-id> \
  "Split Chapter 6 into two separate chapters"

# Merge sections
python SmartFin.py iterate <project-id> \
  "Combine chapters 2 and 3 into a single Overview chapter"
```

### Style Changes 🎨

```bash
# Change writing style
python SmartFin.py iterate <project-id> \
  "Convert the academic tone to a more business-friendly style"

# Adjust formality
python SmartFin.py iterate <project-id> \
  "Make the conclusion more formal and authoritative"

# Change perspective
python SmartFin.py iterate <project-id> \
  "Rewrite chapter 5 from first-person to third-person perspective"
```

## Version Management

### Automatic Versioning

Every iteration creates a new version:

```
storage/project_id/
├── versions/
│   ├── v1_20251005_143022/  # Original
│   ├── v2_20251005_150130/  # After 1st iteration
│   ├── v3_20251005_152045/  # After 2nd iteration
│   └── v4_20251005_154512/  # Current
└── reports/
    └── FINAL_REPORT.md      # Latest version
```

### View Version History

```bash
python SmartFin.py versions <project-id>
```

**Output:**
```
📚 Version History for project_id

v4 (current) - 2025-10-05 15:45:12
   Modification: "Add more technical details to implementation"
   Changes: +347 words, 3 sections modified

v3 - 2025-10-05 15:20:45
   Modification: "Expand case studies section"
   Changes: +892 words, 1 section added

v2 - 2025-10-05 15:01:30
   Modification: "Fix typos and improve clarity"
   Changes: ±124 words, 8 sections modified

v1 - 2025-10-05 14:30:22
   Initial generation
```

### Compare Versions

```bash
python SmartFin.py diff <project-id> v2 v4
```

Shows differences between versions.

### Rollback to Previous Version

```bash
python SmartFin.py rollback <project-id> v2
```

Restores document to version 2.

## Advanced Features

### Targeted Search and Replace

```bash
python SmartFin.py iterate <project-id> \
  --mode search-replace \
  --find "machine learning" \
  --replace "artificial intelligence" \
  --scope all
```

### Batch Iterations

Define multiple changes in a file:

```bash
# iterations.txt
Add case study to chapter 3
Expand technical details in chapter 5
Add conclusion to chapter 7
Update statistics throughout
```

```bash
python SmartFin.py iterate <project-id> --batch iterations.txt
```

### Conditional Iterations

Only modify if condition is met:

```bash
python SmartFin.py iterate <project-id> \
  "Add COVID-19 context if discussing 2020-2025 trends"
```

### Style Transfer

Apply style from another document:

```bash
python SmartFin.py iterate <project-id> \
  --apply-style-from reference_document.md
```

## Iteration Workflow

### Interactive Mode

```bash
python SmartFin.py iterate <project-id> --interactive
```

**Process:**
1. View current content
2. Specify modification
3. Preview changes
4. Approve or reject
5. Apply if approved

### Review Mode

```bash
python SmartFin.py iterate <project-id> \
  "Add examples" \
  --preview-only
```

Shows what would change without applying.

### Auto-approve Mode

```bash
python SmartFin.py iterate <project-id> \
  "Fix grammar and spelling" \
  --auto-approve
```

Applies changes without confirmation.

## Quality Assurance

### Coherence Checking

After iteration, SmartFin checks:
- Logical flow maintained
- No contradictions introduced
- Style consistency preserved
- Transitions smooth

### Automatic Cleanup

- Removes duplicate content
- Fixes broken references
- Updates table of contents
- Renumbers sections

### Validation

```bash
python SmartFin.py validate <project-id>
```

**Checks:**
- Structure integrity
- Citation validity
- Cross-references
- Format compliance

## Performance Optimization

### Iteration Speed Comparison

| Scope | Speed | Use Case |
|-------|-------|----------|
| Local | 30 sec | Typos, small edits |
| Partial | 2-5 min | Multiple sections |
| Global | 5-15 min | Major changes |
| Full Regen | 10-30 min | Complete rewrite |

**Speed Tip:** Prefer targeted iterations over full regeneration.

### Caching

SmartFin caches:
- Document embeddings
- Search results
- Generated sections

Subsequent iterations are faster due to caching.

### Parallel Processing

For batch iterations:

```bash
python SmartFin.py iterate <project-id> \
  --batch changes.txt \
  --parallel
```

Processes independent changes simultaneously.

## Best Practices

### 📝 Clear Instructions

**Good:**
- "Add a table comparing features in the Overview section"
- "Rewrite the introduction to be more engaging"
- "Expand chapter 3 with 2-3 real-world examples"

**Less Effective:**
- "Make it better" (too vague)
- "Fix everything" (unclear scope)
- "Change stuff" (no direction)

### 🎯 Iterative Approach

**Recommended workflow:**

```bash
# Step 1: Generate base content
python SmartFin.py report "Topic"

# Step 2: Review
cat storage/<project-id>/reports/FINAL_REPORT.md

# Step 3: First iteration (structure)
python SmartFin.py iterate <project-id> "Add section on challenges"

# Step 4: Second iteration (content)
python SmartFin.py iterate <project-id> "Expand examples in new section"

# Step 5: Final polish
python SmartFin.py iterate <project-id> "Improve clarity and fix typos"
```

### ⚡ Scope Management

**Use local scope when:**
- Fixing specific errors
- Updating data points
- Minor adjustments

**Use partial scope when:**
- Adding/removing sections
- Reorganizing content
- Expanding specific areas

**Use global scope when:**
- Changing overall style
- Major restructuring
- Adding themes throughout

## Troubleshooting

### Issue: Changes not applied correctly

**Solutions:**
```bash
# Be more specific
python SmartFin.py iterate <project-id> \
  "In Chapter 3, Section 2, add a paragraph about market trends"

# Preview first
python SmartFin.py iterate <project-id> \
  "..." \
  --preview-only
```

### Issue: Lost content after iteration

**Solutions:**
```bash
# Rollback to previous version
python SmartFin.py rollback <project-id> v3

# View version history
python SmartFin.py versions <project-id>
```

### Issue: Iteration too slow

**Solutions:**
```bash
# Use local scope
python SmartFin.py iterate <project-id> \
  "Fix typo in paragraph 3" \
  --scope local

# Reduce model size
--model gpt-4o-mini
```

### Issue: Style inconsistency after multiple iterations

**Solutions:**
```bash
# Run style harmonization
python SmartFin.py harmonize <project-id>

# Reset and regenerate
python SmartFin.py regenerate <project-id> \
  --preserve-content \
  --harmonize-style
```

## API Reference

```bash
python SmartFin.py iterate <project-id> <instruction> [options]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `<project-id>` | str | Required | Project identifier |
| `<instruction>` | str | Required | Modification instruction |
| `--scope` | str | `auto` | Modification scope (local/partial/global/auto) |
| `--preview-only` | flag | `false` | Preview changes without applying |
| `--auto-approve` | flag | `false` | Apply without confirmation |
| `--interactive` | flag | `false` | Interactive iteration mode |
| `--batch` | str | None | Batch iteration file |
| `--mode` | str | `intelligent` | Iteration mode |
| `--preserve-style` | flag | `true` | Maintain original style |
| `--model` | str | `gpt-4o-mini` | LLM model to use |

## Examples

### Report Iteration

```bash
# Initial generation
python SmartFin.py report "Cloud Computing Trends 2025"

# Add content
python SmartFin.py iterate <project-id> \
  "Add a section on serverless computing trends"

# Expand existing
python SmartFin.py iterate <project-id> \
  "Expand the security section with specific examples"

# Update data
python SmartFin.py iterate <project-id> \
  "Update market size figures with latest 2025 data"
```

### PPT Iteration

```bash
# Initial generation
python SmartFin.py ppt "Product Launch Strategy" --slides 18

# Add slides
python SmartFin.py iterate <project-id> \
  "Add 2 slides on competitive analysis after slide 8"

# Improve content
python SmartFin.py iterate <project-id> \
  "Make slide 5 more visual with less text"

# Reorder
python SmartFin.py iterate <project-id> \
  "Move the pricing slide to come before the features slide"
```

## Next Steps

- Learn about [Report Generation](/guide/features/report)
- Try [PPT Creation](/guide/features/ppt)
- Check [Export Formats](/guide/features/export)
