"""Prompt templates for AI analysis tasks."""

# ─── Code Summarization ─────────────────────────────────────────────────────

SUMMARIZE_FILE_PROMPT = """Analyze and summarize the following source code file.

**File:** {file_path}
**Language:** {language}

**Code:**
```{language}
{code}
```

Provide:
1. A brief summary of what this file does (2-3 sentences)
2. Key functions/classes and their purposes
3. Dependencies and imports used
4. Any notable patterns or design decisions

Keep your response concise and technical.
"""

SUMMARIZE_REPO_PROMPT = """Summarize this repository based on its structure and contents.

**Repository:** {repo_name}
**Files:** {file_count}
**Languages:** {languages}

**File Structure:**
{file_tree}

**Key Files:**
{key_files}

Provide:
1. What this project does (1-2 sentences)
2. Architecture overview
3. Main components and their roles
4. Tech stack observed

Keep your response concise.
"""

# ─── PR Review ───────────────────────────────────────────────────────────────

PR_REVIEW_PROMPT = """Review the following code changes from a pull request.

**PR:** {pr_id}
**Changed Files:** {changed_files}

**Diff:**
```
{diff}
```

**Context (related code):**
{context}

Analyze and provide:
1. **Risk Score** (0.0 to 1.0) — likelihood of introducing bugs
2. **Summary** — what the PR does in 1-2 sentences
3. **Suggestions** — specific, actionable review comments with file and line references
4. **Bug Risks** — any potential bugs or regressions

Format suggestions as:
- [file:line] severity: message
"""

# ─── Bug Detection ───────────────────────────────────────────────────────────

BUG_DETECTION_PROMPT = """Analyze the following code for potential bugs, security issues, and code smells.

**File:** {file_path}
**Language:** {language}

```{language}
{code}
```

Look for:
1. Null/undefined reference risks
2. Resource leaks (unclosed files, connections)
3. Race conditions or concurrency issues
4. Security vulnerabilities (injection, hardcoded secrets)
5. Logic errors and off-by-one mistakes
6. Error handling gaps

Format each finding as:
- [line N] severity (critical/warning/info): description
"""

# ─── Codebase Chat ───────────────────────────────────────────────────────────

CHAT_SYSTEM_PROMPT = """You are NEXUS AI, an intelligent assistant that helps developers understand and work with their codebase.

You have access to:
- Semantic search results from the codebase
- Dependency graph information
- Code structure analysis

When answering questions:
1. Reference specific files and functions when possible
2. Explain code behavior clearly
3. Suggest improvements when relevant
4. Be concise but thorough
"""

CHAT_WITH_CONTEXT_PROMPT = """Based on the following codebase context, answer the user's question.

**Relevant Code Snippets:**
{context}

**Dependency Information:**
{dependencies}

**User Question:** {question}

Provide a clear, technical answer referencing the specific code shown above.
"""
