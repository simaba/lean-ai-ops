# Public interface contract

The public interface is an additive presentation layer over Lean AI Ops. It is intentionally separated from the working Python runtime.

## Goals

1. Make the project understandable before installation.
2. Expose the DMAIC journey, evidence model, analysis choices, and architecture visually.
3. Provide a safe deterministic browser demo with no API call and no persistence.
4. Keep working assessment and statistical behavior inside the tested Python application.
5. Make the website structure reusable through \`project-manifest.json\` rather than coupling the design to a single README.

## Layering

\`\`\`text
Repository contracts and sample data
              |
              +--> Static public interface (GitHub Pages)
              |      - orientation
              |      - deterministic demo
              |      - architecture / tool explorers
              |
              +--> Streamlit application
                     - assessment generation
                     - analytics workbench
                     - project persistence
                     - exports
                     - optional Anthropic integration
\`\`\`

## Truthfulness requirements

The static site must never imply that it:

- executes the Python assessment engine;
- calls an AI model;
- validates root causes;
- performs the repository's statistical calculations;
- stores a project;
- produces a certified Lean Six Sigma conclusion.

Browser-only output is therefore labelled **deterministic** and framed as a starter brief or explainer.

## Reusable manifest

\`project-manifest.json\` is the stable interface between project metadata and future site tooling. A repository adopting the same pattern should be able to declare:

- project name and tagline;
- runtime and public-interface type;
- capabilities;
- primary journeys;
- analytics or tool families;
- evidence states;
- output formats;
- boundaries between demo and working runtime.

This is deliberately small. It can evolve with a versioned schema if more repositories adopt the interface pattern.

## Deployment

\`.github/workflows/pages.yml\` publishes \`docs/\` as a Pages artifact when matching changes reach \`main\`. Deployment actions are pinned to commit SHAs. GitHub Pages must use **GitHub Actions** as its source for the first deployment.
