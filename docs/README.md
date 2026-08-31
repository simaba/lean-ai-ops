# Public interface

\`docs/\` contains the static public interface for Lean AI Ops. It is deployable on GitHub Pages without a JavaScript build step or third-party runtime dependency.

## Boundary

The site is an orientation and deterministic browser demo. It **does not execute the Python assessment engine, call Anthropic, persist projects, or run the statistical workbench**. Those capabilities remain in the Streamlit application.

## Structure

- \`index.html\` — public product interface
- \`assets/styles.css\` — responsive visual system
- \`assets/app.js\` — DMAIC explorer, tool explorer, architecture inspector, theme state, and deterministic starter brief
- \`project-manifest.json\` — machine-readable capability and interface manifest intended to make the pattern reusable
- \`data/sample-project.json\` — sanitized demo contract
- existing \`*.md\` documents — deeper implementation and methodology notes

## Local preview

From the repository root:

\`\`\`bash
python -m http.server 8000 --directory docs
\`\`\`

Open \`http://localhost:8000\`.

## Deployment

\`.github/workflows/pages.yml\` packages this directory and deploys it through GitHub Pages after matching changes reach \`main\`. The repository Pages source must be set to **GitHub Actions** once for deployment to become active.
