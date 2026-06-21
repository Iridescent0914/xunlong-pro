# Export Formats

SmartFin supports multiple export formats to suit different use cases and platforms.

## Overview

Export your content to:
- 📝 Markdown (.md)
- 🌐 HTML (.html)
- 📄 PDF (.pdf)
- 📃 DOCX (.docx)
- 📊 PPTX (.pptx)
- 📚 EPUB (.epub)

## Quick Start

```bash
# Export to single format
python SmartFin.py export <project-id> --format pdf

# Export to multiple formats
python SmartFin.py export <project-id> --format md,html,pdf,docx
```

## Markdown Export

### Features

- ✅ Clean, readable text
- ✅ Version control friendly
- ✅ Platform-agnostic
- ✅ Easy to edit
- ✅ GitHub/GitLab compatible

### Usage

```bash
python SmartFin.py export <project-id> --format md
```

### Output Structure

```markdown
# Report Title

## Table of Contents
- [Introduction](#introduction)
- [Main Content](#main-content)
- [Conclusion](#conclusion)

## Introduction

Content here...

## References

[1] Source citation
```

### Options

```bash
# Include table of contents
python SmartFin.py export <project-id> \
  --format md \
  --include-toc

# Add metadata
python SmartFin.py export <project-id> \
  --format md \
  --include-metadata
```

### Best For

- Documentation
- GitHub repositories
- Version-controlled content
- Plain text workflows
- Cross-platform sharing

## HTML Export

### Features

- ✅ Professional styling
- ✅ Responsive design
- ✅ Interactive elements
- ✅ Print-ready
- ✅ Browser-compatible

### Usage

```bash
python SmartFin.py export <project-id> --format html
```

### Templates

```bash
# Business template
python SmartFin.py export <project-id> \
  --format html \
  --template business

# Academic template
python SmartFin.py export <project-id> \
  --format html \
  --template academic

# Minimal template
python SmartFin.py export <project-id> \
  --format html \
  --template minimal
```

### Customization

```bash
# Custom CSS
python SmartFin.py export <project-id> \
  --format html \
  --css custom_styles.css

# Inline styles
python SmartFin.py export <project-id> \
  --format html \
  --inline-css
```

### Features

**Table of Contents:**
- Sticky navigation
- Auto-scrolling
- Collapsible sections

**Code Highlighting:**
- Syntax highlighting
- Copy button
- Line numbers

**Responsive:**
- Mobile-friendly
- Print-optimized
- Dark mode support

### Best For

- Web publishing
- Email distribution
- Corporate intranets
- Online documentation
- Shareable reports

## PDF Export

### Features

- ✅ Professional layout
- ✅ Fixed formatting
- ✅ Print-ready
- ✅ Page numbers
- ✅ Headers/footers
- ✅ Bookmarks

### Usage

```bash
python SmartFin.py export <project-id> --format pdf
```

### Page Settings

```bash
# Letter size (US)
python SmartFin.py export <project-id> \
  --format pdf \
  --page-size letter

# A4 size (International)
python SmartFin.py export <project-id> \
  --format pdf \
  --page-size a4

# Custom margins
python SmartFin.py export <project-id> \
  --format pdf \
  --margins "1in,1in,1in,1in"  # top,right,bottom,left
```

### Headers and Footers

```bash
python SmartFin.py export <project-id> \
  --format pdf \
  --header-left "Report Title" \
  --header-right "Company Name" \
  --footer-left "Confidential" \
  --footer-center "Page {page} of {total}" \
  --footer-right "Date: {date}"
```

### Quality Options

```bash
# Print quality (high DPI)
python SmartFin.py export <project-id> \
  --format pdf \
  --quality print

# Screen quality (lower file size)
python SmartFin.py export <project-id> \
  --format pdf \
  --quality screen

# Draft quality (fastest)
python SmartFin.py export <project-id> \
  --format pdf \
  --quality draft
```

### Advanced Features

**Bookmarks:**
Automatic PDF bookmarks from headings

**Hyperlinks:**
Clickable internal and external links

**Metadata:**
```bash
python SmartFin.py export <project-id> \
  --format pdf \
  --title "Report Title" \
  --author "Author Name" \
  --subject "Report Subject" \
  --keywords "AI,trends,2025"
```

**Password Protection:**
```bash
python SmartFin.py export <project-id> \
  --format pdf \
  --password "SecurePassword123"
```

### Best For

- Official documents
- Client deliverables
- Print publication
- Archival
- Formal reports

## DOCX Export

### Features

- ✅ Microsoft Word compatible
- ✅ Editable formatting
- ✅ Track changes ready
- ✅ Comments support
- ✅ Collaboration-friendly

### Usage

```bash
python SmartFin.py export <project-id> --format docx
```

### Styling

```bash
# Apply Word template
python SmartFin.py export <project-id> \
  --format docx \
  --template corporate_template.docx

# Custom styles
python SmartFin.py export <project-id> \
  --format docx \
  --heading-style "Arial,16,bold" \
  --body-style "Calibri,11,normal"
```

### Features

**Styles:**
- Heading levels (1-6)
- Paragraph styles
- Character styles
- Table styles

**Elements:**
- Tables
- Images
- Lists (bulleted/numbered)
- Page breaks
- Section breaks

**Metadata:**
```bash
python SmartFin.py export <project-id> \
  --format docx \
  --title "Document Title" \
  --author "Author Name" \
  --company "Company Name"
```

### Best For

- Corporate documents
- Collaborative editing
- Track changes workflows
- Client revisions
- Microsoft Office environments

## PPTX Export

### Features

- ✅ PowerPoint compatible
- ✅ Professional design
- ✅ Editable slides
- ✅ Speaker notes
- ✅ Animations (optional)

### Usage

```bash
python SmartFin.py export <project-id> --format pptx
```

### Themes

```bash
# Apply theme
python SmartFin.py export <project-id> \
  --format pptx \
  --theme business-blue

# Custom colors
python SmartFin.py export <project-id> \
  --format pptx \
  --primary-color "#2E86AB" \
  --accent-color "#F18F01"
```

### Slide Layouts

Automatic layout selection:
- Title slides
- Content slides
- Two-column layouts
- Image slides
- Chart slides
- Section headers

### Features

**Speaker Notes:**
Included automatically if available

**Animations:**
```bash
python SmartFin.py export <project-id> \
  --format pptx \
  --animations subtle
```

**Master Slides:**
Consistent formatting across all slides

### Best For

- Presentations
- Pitch decks
- Training materials
- Conference talks
- Client presentations

## EPUB Export

### Features

- ✅ E-reader compatible
- ✅ Reflowable text
- ✅ Adjustable font size
- ✅ Table of contents
- ✅ Metadata support

### Usage

```bash
python SmartFin.py export <project-id> --format epub
```

### Metadata

```bash
python SmartFin.py export <project-id> \
  --format epub \
  --title "Book Title" \
  --author "Author Name" \
  --publisher "Publisher Name" \
  --isbn "978-1234567890" \
  --language "en"
```

### Cover Image

```bash
python SmartFin.py export <project-id> \
  --format epub \
  --cover cover_image.jpg
```

### Features

**Navigation:**
- Automatic TOC
- Chapter navigation
- Bookmarks

**Formatting:**
- Semantic HTML
- CSS styling
- Custom fonts (embedded)

**Compatibility:**
- Kindle (via conversion)
- Apple Books
- Google Play Books
- Kobo
- Nook

### Best For

- E-books
- Long-form content
- Mobile reading
- Digital publishing

## Batch Export

### Export All Formats

```bash
python SmartFin.py export <project-id> --format all
```

Generates:
- Markdown
- HTML
- PDF
- DOCX
- PPTX (if applicable)
- EPUB (if applicable)

### Selective Export

```bash
python SmartFin.py export <project-id> \
  --format md,pdf,docx
```

### Export Multiple Projects

```bash
python SmartFin.py export-batch \
  --projects project1,project2,project3 \
  --format pdf
```

## Advanced Options

### Compression

```bash
# Compress images
python SmartFin.py export <project-id> \
  --format pdf \
  --compress-images \
  --image-quality 85

# Optimize file size
python SmartFin.py export <project-id> \
  --format docx \
  --optimize-size
```

### Watermarks

```bash
# Text watermark
python SmartFin.py export <project-id> \
  --format pdf \
  --watermark "CONFIDENTIAL" \
  --watermark-opacity 0.3

# Image watermark
python SmartFin.py export <project-id> \
  --format pdf \
  --watermark-image logo.png
```

### Custom Output Path

```bash
python SmartFin.py export <project-id> \
  --format pdf \
  --output /path/to/custom/location.pdf
```

### Post-Processing

```bash
# Run custom script after export
python SmartFin.py export <project-id> \
  --format pdf \
  --post-process "<your-script-path>"
```

## Export Comparison

| Format | Editable | Print | Web | Mobile | Collaboration |
|--------|----------|-------|-----|--------|---------------|
| **MD** | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| **HTML** | ⚠️ | ✅ | ✅ | ✅ | ⚠️ |
| **PDF** | ❌ | ✅ | ✅ | ✅ | ⚠️ |
| **DOCX** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| **PPTX** | ✅ | ✅ | ⚠️ | ⚠️ | ✅ |
| **EPUB** | ❌ | ⚠️ | ⚠️ | ✅ | ❌ |

**Legend:**
- ✅ Excellent
- ⚠️ Partial/Limited
- ❌ Not suitable

## Format Selection Guide

### Choose Markdown when:
- Working with version control (Git)
- Need maximum editability
- Want platform independence
- Creating documentation

### Choose HTML when:
- Publishing to web
- Need responsive design
- Want interactive elements
- Email distribution

### Choose PDF when:
- Need fixed layout
- Printing required
- Official documents
- Archival purposes

### Choose DOCX when:
- Microsoft Office environment
- Collaborative editing needed
- Track changes required
- Client expects Word format

### Choose PPTX when:
- Creating presentations
- Need slide format
- Pitch decks
- Training materials

### Choose EPUB when:
- Publishing e-books
- Mobile reading
- E-reader distribution

## Troubleshooting

### Issue: Formatting lost in export

**Solutions:**
```bash
# Use template
--template business

# Preserve styles
--preserve-styles

# Check source format quality
python SmartFin.py validate <project-id>
```

### Issue: Large file size

**Solutions:**
```bash
# Compress images
--compress-images --image-quality 75

# Optimize
--optimize-size

# Use screen quality for PDF
--quality screen
```

### Issue: Export failed

**Solutions:**
```bash
# Check logs
cat storage/<project-id>/logs/export.log

# Verify format support
python SmartFin.py export-formats

# Try different format
python SmartFin.py export <project-id> --format md
```

### Issue: Fonts not embedded (PDF)

**Solutions:**
```bash
# Embed fonts
python SmartFin.py export <project-id> \
  --format pdf \
  --embed-fonts
```

## API Reference

```bash
python SmartFin.py export <project-id> [options]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `<project-id>` | str | Required | Project identifier |
| `--format` | str | `md` | Export format(s) |
| `--output` | str | Auto | Custom output path |
| `--template` | str | `default` | Template to use |
| `--quality` | str | `high` | Output quality |
| `--compress-images` | flag | `false` | Compress images |
| `--optimize-size` | flag | `false` | Optimize file size |
| `--watermark` | str | None | Watermark text |
| `--password` | str | None | Password protect (PDF) |
| `--include-toc` | flag | `true` | Include table of contents |
| `--include-metadata` | flag | `true` | Include metadata |

## Examples

### Professional Report

```bash
python SmartFin.py export <project-id> \
  --format pdf,docx \
  --template business \
  --header-left "Q4 Report 2025" \
  --header-right "Company Inc." \
  --footer-center "Page {page} of {total}" \
  --watermark "CONFIDENTIAL"
```

### Academic Paper

```bash
python SmartFin.py export <project-id> \
  --format pdf \
  --template academic \
  --page-size a4 \
  --quality print \
  --include-toc \
  --embed-fonts
```

### Web Documentation

```bash
python SmartFin.py export <project-id> \
  --format html \
  --template minimal \
  --inline-css \
  --optimize-size
```

### Presentation Deck

```bash
python SmartFin.py export <project-id> \
  --format pptx \
  --theme corporate-blue \
  --animations subtle \
  --include-speaker-notes
```

## Next Steps

- Learn about [Report Generation](/guide/features/report)
- Try [PPT Creation](/guide/features/ppt)
- Understand [Content Iteration](/guide/features/iteration)
