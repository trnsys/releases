# releases

Shared release artifacts for TRNSYS components.

Each component publishes cross-compiled binaries here as GitHub releases. Tags are prefixed with the component name to avoid collisions:

| Component | Tag pattern | Source |
|---|---|---|
| trn | `trn-vX.Y.Z` | [trnsys/trn](https://github.com/trnsys/trn) |

Release workflows in each source repo handle building, packaging, and publishing here via a GitHub App token. Do not create releases manually.
