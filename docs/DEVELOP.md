# Developer Guide

This guide provides instructions for maintaining and extending the Chicory documentation.

## Adding a New Cookbook

Follow these steps to add a new cookbook to the documentation:

### 1. Create Cookbook Directory Structure

```bash
# Create the main cookbook directory
mkdir -p how-to-guides/cookbooks/[cookbook-name]

# Create subdirectories
cd how-to-guides/cookbooks/[cookbook-name]
mkdir docs images
```

### 2. Create Required Files

#### Main README.md
Create `how-to-guides/cookbooks/[cookbook-name]/README.md` with this template:

```markdown
# [Cookbook Title]

Brief description of what this cookbook covers and its target audience.

---

## Quick Start

1. Step 1 overview
2. Step 2 overview
3. Step 3 overview
4. Step 4 overview
5. Step 5 overview

---

## Contents

- [Section 1](docs/1-section-name.md) - Description
- [Section 2](docs/2-section-name.md) - Description
- [Section 3](docs/3-section-name.md) - Description

---

## What You'll Learn

- **Topic 1**: Brief description
- **Topic 2**: Brief description
- **Topic 3**: Brief description

---

## Prerequisites

- Requirement 1
- Requirement 2
- Requirement 3

---

```

#### Individual Documentation Files
Create `docs/1-[section-name].md`, `docs/2-[section-name].md`, etc.:

```markdown
# [Section Title]

Brief introduction to this section.

{% stepper %}
{% step %}

### Step Title

Step content with clear instructions.

<img src="../images/image-name.png" alt="Description" style="width:50%;"/>

{% endstep %}

{% step %}

### Next Step Title

Continue with next step content.

{% hint style="success" %}
**Tip:** Helpful tip for users.
{% endhint %}

{% endstep %}
{% endstepper %}
```

### 3. Update SUMMARY.md

Add your cookbook to `/SUMMARY.md` in the cookbooks section:

```markdown
## Reference Guides

* [How-to Guides](how-to-guides/README.md)
  * [Cookbooks](how-to-guides/cookbooks/README.md)
    * [Your New Cookbook](how-to-guides/cookbooks/[cookbook-name]/README.md)
      * [Section 1](how-to-guides/cookbooks/[cookbook-name]/docs/1-section-name.md)
      * [Section 2](how-to-guides/cookbooks/[cookbook-name]/docs/2-section-name.md)
      * [Section 3](how-to-guides/cookbooks/[cookbook-name]/docs/3-section-name.md)
```

### 4. Update Cookbooks Index

Add your cookbook to `/how-to-guides/cookbooks/README.md`:

```markdown
## Available Cookbooks

* [**Your New Cookbook**](cookbook-name/README.md) - Brief description
```

## Documentation Standards

### Writing Style
- **Concise and Direct**: Keep explanations clear and to the point
- **Step-by-Step**: Use numbered lists and stepper components for processes
- **Visual**: Include screenshots and diagrams where helpful
- **Consistent Terminology**: Use established Chicory terms (e.g., "Scan Context" not "Train")

### Formatting Guidelines

#### Use GitBook Components
```markdown
{% stepper %}
{% step %}
Content here
{% endstep %}
{% endstepper %}

{% hint style="success" %}
Success tips and best practices
{% endhint %}

{% hint style="warning" %}
Important warnings or cautions
{% endhint %}

{% code overflow="wrap" %}
```
Code blocks
```
{% endcode %}
```

#### Image Guidelines
- Store images in the `images/` directory
- Use descriptive filenames: `agent-creation-form.png`
- Include alt text and sizing: `<img src="../images/file.png" alt="Description" style="width:50%;"/>`
- Use consistent sizing (25%, 50%, 75% based on content importance)

#### Link Formatting
- Internal links: `[Link Text](../path/to/file.md)`
- External links: `[Link Text](https://example.com)`
- Bold important links: `[**Important Link**](path.md)`

### File Naming Conventions
- Use kebab-case for directories: `building-your-first-agent`
- Use kebab-case for files: `1-agent-creation.md`
- Number documentation files: `1-`, `2-`, `3-` for logical ordering
- Use descriptive names: `agent-creation` not `create`

### Content Structure
Each cookbook should follow the ADLC (Agent Development Life Cycle):
1. **Build** - Setup and creation steps
2. **Evaluate** - Testing and validation
3. **Evolve** - Iteration and improvement
4. **Deploy** - Production deployment
5. **Monitor** - Ongoing management

## Cross-References

### Link to Other Documentation
- Always link to the quickstart for basic concepts
- Reference the main Building Your First Agent cookbook for foundational knowledge
- Link to API support for technical help

### Update Related Files
When adding a new cookbook, check if these files need updates:
- `/README.md` - Main introduction page
- `/how-to-guides/README.md` - How-to guides index
- Any related cookbooks that might benefit from cross-references

## Testing Your Changes

### Check Links
Verify all internal links work:
```bash
# Test relative paths work correctly
find . -name "*.md" -exec grep -l "\]\(" {} \;
```

### Validate Structure
Ensure SUMMARY.md reflects your new content and maintains proper hierarchy.

### Review Content
- Does it follow the established tone and style?
- Are all steps clear and actionable?
- Do images render properly?
- Are there appropriate hints and tips?

## Common Patterns

### API Examples
When showing API calls, use this format:
```bash
curl -X POST https://app.chicory.ai/api/v1/endpoint \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -d '{
    "key": "value"
  }'
```

### Configuration Examples
Use proper YAML/JSON formatting:
```yaml
# Example configuration
name: example-agent
description: Description here
instructions: |
  Your agent instructions here
```

### Prerequisites Sections
Always include clear prerequisites:
- Access to Chicory AI dashboard
- Required permissions or tokens
- Prerequisite knowledge or completed guides

## Adding Best Practices

Best practices are external resources that provide guidance on using Chicory effectively.

### 1. Update Best Practices Index

Add your best practice to `/how-to-guides/best-practices/README.md`:

```markdown
## Best Practices

* [**Practice Title**](https://external-link.com) - Brief description of the best practice
* [**Another Practice**](https://external-link.com) - Description
```

### 2. Content Guidelines for Best Practices

When curating external best practice resources:

#### Selection Criteria
- **Authoritative Source**: From Chicory team, partners, or recognized experts
- **Practical Value**: Provides actionable guidance for real-world scenarios  
- **Current**: Information is up-to-date with latest Chicory features
- **Complementary**: Adds value beyond existing documentation

#### Categories
Organize best practices by topic:
- **Agent Design Patterns**
- **Data Integration Strategies** 
- **Performance Optimization**
- **Security & Governance**
- **Team Collaboration**
- **Production Deployment**

#### Link Format
```markdown
* [**[Category] Practice Title**](https://external-link.com) - Brief description highlighting key takeaways and target audience
```

### 3. Update SUMMARY.md

Ensure best practices appear in navigation:

```markdown
## Reference Guides

* [How-to Guides](how-to-guides/README.md)
  * [Best-Practices](how-to-guides/best-practices/README.md)
```

## Adding Blogs

Blogs are external articles and posts about Chicory use cases, tutorials, and insights.

### 1. Update Blogs Index

Add your blog post to `/how-to-guides/blogs/README.md`:

```markdown
## Blog Posts

### Recent Posts

* [**Blog Title**](https://external-link.com) - Brief description and date
* [**Another Post**](https://external-link.com) - Description and date

### By Category

#### Use Cases & Success Stories
* [**Customer Success: Company X**](https://external-link.com) - How Company X achieved results with Chicory

#### Tutorials & Guides  
* [**Advanced Agent Patterns**](https://external-link.com) - Deep dive into complex agent configurations

#### Platform Updates
* [**New Features Announcement**](https://external-link.com) - Latest platform capabilities
```

### 2. Content Guidelines for Blogs

When curating external blog content:

#### Content Types
- **Use Cases**: Real-world implementations and success stories
- **Tutorials**: Step-by-step guides for specific scenarios
- **Platform Updates**: New features and capabilities announcements  
- **Technical Deep Dives**: Advanced topics and architectural discussions
- **Community Contributions**: User-generated content and case studies

#### Organization
- **Chronological**: Most recent posts first
- **Categorical**: Group by content type or topic
- **Difficulty**: Beginner, intermediate, advanced indicators

#### Link Format
```markdown
* [**Blog Title**](https://external-link.com) - Brief description, publication date, and difficulty level if applicable
```

### 3. Update SUMMARY.md

Ensure blogs appear in navigation:

```markdown
## Reference Guides

* [How-to Guides](how-to-guides/README.md)
  * [Blogs](how-to-guides/blogs/README.md)
```

## External Link Management

### Link Validation
Regular checks for external resources:

```bash
# Check external links periodically
grep -r "https://" how-to-guides/best-practices/
grep -r "https://" how-to-guides/blogs/
```

### Link Guidelines
- **HTTPS**: Always use secure links
- **Persistent URLs**: Prefer permanent links over temporary ones
- **Archive**: Consider archive.org links for critical resources
- **Descriptions**: Include publication date and brief summary
- **Categories**: Use consistent categorization for easy discovery

### Broken Link Handling
When external links break:
1. **Check Archive**: Look for archived versions
2. **Find Alternative**: Search for updated or moved content  
3. **Remove If Necessary**: Remove if content is no longer relevant
4. **Update Description**: Note if link is archived or alternative

## Maintenance

### Regular Updates
- Keep screenshots current with UI changes
- Update API examples when endpoints change
- Verify external links remain valid (quarterly review recommended)
- Review content for accuracy with platform updates
- Curate new best practices and blog content monthly

### External Content Review
- **Monthly**: Check for new relevant blog posts and best practices
- **Quarterly**: Validate all external links are still active
- **Bi-annually**: Review relevance of all external content

### Version Control
- Use descriptive commit messages
- Group related changes in single commits
- Update documentation alongside feature releases
- Tag external content additions with dates for tracking