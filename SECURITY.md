# Security Policy

## Reporting a vulnerability

Please report security issues privately to **oogisoogi@gmail.com**.
Do not open public issues for vulnerabilities. You should receive a response
within a few days; coordinated disclosure is appreciated.

## Scope notes

- The desktop app talks to a local daemon (`cysd`) over a user-owned Unix socket
  (macOS/Linux) or a DACL-sealed named pipe (Windows). No network listener is opened.
- New releases are verified: app binaries via their distribution signature plus our
  release feed's two minisign layers (envelope + release body), checked by the daemon's
  auto-update before it installs anything; packs via minisign
  (`pack-manifest.json.minisig`, key pinned in the binary).
- External URL opening is gated by a hard host allowlist
  (`~/.cys/url-allow-hosts` / `CYS_URL_ALLOW_HOSTS` extend it locally only).
- A pre-publish secret/PII gate exists at `scripts/secret-scan.sh --all`
  (fail-closed; static pattern matching — see its header for honest limits).
