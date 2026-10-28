# Agents

This repo owns the non-Omarchy Linux entry point and OS-specific guidance. The shared provisioning implementation currently lives in `groundwork-mac`; change its managed files there instead of copying them here. Never apply this environment to Omarchy.

Engineering work follows Compass: start at `.compass/COMPASS.md`, with terms in `.compass/TERMINOLOGY.md`. Load `skills/reviewable-agent-workspaces/SKILL.md` before implementation or worktree changes, `skills/concurrent-agent-runtimes/SKILL.md` before starting or inspecting concurrent processes, and `skills/repeatable-agent-execution/SKILL.md` before the first edit in a checkout and before final proof. Selected skills, loaded from `skills/` when a task touches their area: `acceptance-evidence`, `accessible-product-development`, `agent-orchestration`, `ai-backend-change`, `ci-workflow-change`, `dependency-change`, `developer-tool-change`, `field-failure-backpressure`, `github-delivery-workflow`, `inclusive-content-design`, `inclusive-product-foundation`, `independent-code-review`, `internationalization-first`, `performance-sensitive-change`, `privacy-by-design`, `repo-contribution-etiquette`, `secure-by-design`, `shell-script-change`, `terminal-program-ux`, `testing-strategy`, `toolchain-authority`. GitHub writes follow `repo-contribution-etiquette` (act as the account that owns the repository).

Use [groundwork-core](https://github.com/jasondockery/groundwork-core) for shared operational docs and tailnet policy. Keep original `groundwork` unchanged and available for curriculum and historical context.

Omarchy's keybindings and conventions are the target where they fit. T3 Code Nightly and Herdr must stay available through the shared engine, with local provider authentication. Do not restore old Groundwork shortcuts merely because they appear in historical docs.

Parse arguments before side effects. Help and invalid input must not mutate anything. Preserve local configuration, SSH credentials, Git identities, and old checkouts during migration. Run Bash syntax and isolated wrapper tests for changes; never claim native desktop, package, or cross-machine acceptance from fixtures.
