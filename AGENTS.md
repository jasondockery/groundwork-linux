# Agents

This repo owns the non-Omarchy Linux entry point and OS-specific guidance. The shared provisioning implementation currently lives in `groundwork-mac`; change its managed files there instead of copying them here. Never apply this environment to Omarchy.

Use [Compass](https://github.com/jasondockery/compass/blob/main/COMPASS.md) and its applicable skills for shared engineering guidance. Use [groundwork-core](https://github.com/jasondockery/groundwork-core) for shared operational docs and tailnet policy. These links are references, not a claim of receipt-verified projection. Keep original `groundwork` unchanged and available for curriculum and historical context.

Omarchy's keybindings and conventions are the target where they fit. T3 Code Nightly and Herdr must stay available through the shared engine, with local provider authentication. Do not restore old Groundwork shortcuts merely because they appear in historical docs.

Parse arguments before side effects. Help and invalid input must not mutate anything. Preserve local configuration, SSH credentials, Git identities, and old checkouts during migration. Run Bash syntax and isolated wrapper tests for changes; never claim native desktop, package, or cross-machine acceptance from fixtures.
