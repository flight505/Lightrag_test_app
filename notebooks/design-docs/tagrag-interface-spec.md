# Tagrag Interface Spec

## Markdown format
---
user-prompt: `INPUT[{user-prompt}]` #{YYYY-MM-DD}

## ${user-prompt-summary}
> [!inquiry]- [[#light-global/gpt-4o/eng/1]] #ds/${shahash12}
> user-prompt: ${user-prompt}
> rag: ${rag} // light-naive, light-local, light-global, light-hybrid
> ai-model: gpt-4o
> languages: eng
> embedder: ollama-nomic-embed-text
> template: [[Obsidian Researcher Note]]
> user-prompt-summary: ${user-prompt-summary}
> user-prompt-rewritten: ${user-prompt-rewritten}
> prompt-hash: ${shahash12}

> [!sources]- #toggle {sources-count} sources
> ### Websearch (top 3 web sources)
> [^1] {source-1}
> [^2] {source-2}
> [^3] {source-3}
> ### Doc Graph (top 3 docs) [^4]
> - {list-of-docs-used}

> [!answer]+ Answered by {rag}@{ai-model} 🗓️{date}
> subprompt-steps: ${subprompt-steps}
> {answer}

> [!footer]- {edit} | {rewrite} | {copy} | {import}

## ${user-prompt-summary} edit-2
> [!inquiry]- [[#light-global/gpt-4o/eng/1]] #ds/${shahash12}
> ...

> [!sources]- #toggle {sources-count} sources
> ...

> [!answer]+ Answered by {rag}@{ai-model} 🗓️{date}
> subprompt-steps: ${subprompt-steps}
> {answer}

> [!footer]- {edit} | {rewrite} | {copy} | {import}

...