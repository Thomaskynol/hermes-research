# Daytona OpenCode Plugin: Technical Report

## Executive Summary

This report synthesizes documentation from multiple official sources regarding the Daytona OpenCode plugin (`@daytona/opencode`), an integration that runs OpenCode AI coding agent sessions within isolated Daytona sandbox environments. The plugin provides secure session isolation, persistent sandbox state, live preview links, and automatic Git synchronization to local branches.

---

## 1. Product Overview

### 1.1 Purpose
The Daytona OpenCode plugin automatically provisions a dedicated Daytona sandbox for each OpenCode session. Sandboxes persist until the corresponding OpenCode session is deleted, and all file changes are synchronized to a local Git branch for review and merge.

### 1.2 Core Value Proposition
| Capability | Description |
|------------|-------------|
| **Secure Isolation** | Each OpenCode session executes in its own remote sandbox environment |
| **Persistence** | Sandbox state survives across interactions until explicit session deletion |
| **Live Previews** | Automatic generation of preview URLs when a server process starts in the sandbox |
| **Git Synchronization** | Changes in the sandbox are synced to a local Git branch for human review |
| **Zero-Config Runtime** | No wrapper scripts required; plugin activates automatically when listed in `opencode.json` |

---

## 2. Installation & Configuration

### 2.1 Project-Level Installation
Add the plugin to the project's `opencode.json`:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@daytona/opencode"]
}
```
OpenCode downloads the plugin automatically on startup.  
*Sources: Daytona docs, daytona/integrations README, Goober-Codes/daytona-pi README*

### 2.2 Global Installation
Edit the user-level configuration at `~/.config/opencode/opencode.json` with the same `plugin` entry.  
*Sources: Daytona docs, daytona/integrations README, Goober-Codes/daytona-pi README*

### 2.3 Environment Requirements
- **Daytona account** (required)
- **Daytona API key** (required)

Set via environment variable:
```bash
export DAYTONA_API_KEY="your-api-key"
```
Or via `.env` file in project root:
```
DAYTONA_API_KEY=your-api-key
```
*Sources: Daytona docs, daytona/integrations README, Goober-Codes/daytona-pi README*

### 2.4 Prerequisites
- Git repository initialized (`git init`) to enable sandbox-to-local sync  
*Sources: Daytona docs, Goober-Codes/daytona-pi README*

---

## 3. Operational Workflow

1. **Initialize Git** (if not already): `git init`
2. **Configure API key** (environment or `.env`)
3. **Start OpenCode**: `opencode`
4. **Session begins** → Plugin provisions a Daytona sandbox
5. **Work proceeds** → File changes sync to a local Git branch
6. **Server starts in sandbox** → Live preview link generated automatically
7. **Session ends** → Sandbox persists until session is deleted

*Sources: Daytona docs, daytona/integrations README, Goober-Codes/daytona-pi README*

---

## 4. Technical Architecture

### 4.1 Package Structure (daytona/integrations repository)
```
packages/opencode-plugin/
├── .opencode/plugin/          # Plugin source (TypeScript)
│   ├── daytona/               # Main Daytona integration
│   └── index.ts               # Plugin entry point (compiled to .js in place)
├── package.json               # Package metadata, build script
├── tsconfig.json              # TypeScript configuration
└── README.md
```
*Source: daytona/integrations README*

### 4.2 Package Structure (Goober-Codes/daytona-pi monorepo)
```
libs/opencode-plugin/
├── .opencode/                 # Source TypeScript files
│   ├── plugin/
│   │   ├── daytona/           # Main Daytona integration
│   │   └── index.ts           # Plugin entry point
├── dist/                      # Build output
│   └── .opencode/             # Compiled JavaScript files
├── package.json
├── project.json               # Nx build configuration
├── tsconfig.json
├── tsconfig.lib.json
└── README.md
```
*Source: Goober-Codes/daytona-pi README*

### 4.3 Dependency Note (from OpenDock listing)
- `@daytona/sdk` is a **peer dependency** (load-bearing)
- The plugin branches on `err instanceof DaytonaNotFoundError` to distinguish "sandbox gone, replace it" from "transient failure, keep session mapping"
- Duplicate SDK copies in the dependency tree can cause silent check failures
- Unit test `tests/unit/exports.test.ts` fails loudly if this regresses  
*Source: OpenDock plugin page*

---

## 5. Development & Publishing

### 5.1 Local Development
- With a symlink, OpenCode loads TypeScript source directly—no build step required  
*Source: Goober-Codes/daytona-pi README*

### 5.2 Build Command
```bash
npx nx run opencode-plugin:build
```
Compiles `.opencode/` TypeScript sources to `dist/.opencode/` JavaScript.  
*Source: Goober-Codes/daytona-pi README*

### 5.3 Local Testing of Built Package
```bash
mkdir -p ~/myproject && cd ~/myproject
mkdir -p .opencode/plugins
cat > .opencode/plugins/daytona-local.js << 'EOF'
module.exports = require('[ABSOLUTE_PATH_TO_DAYTONA]/dist/libs/opencode-plugin/.opencode/plugin')
EOF
git init
opencode
```
*Source: Goober-Codes/daytona-pi README*

### 5.4 Publishing
```bash
npm login
npx nx run opencode-plugin:publish
```
Publishes to npm with public access using version from `package.json`.  
*Source: Goober-Codes/daytona-pi README*

---

## 6. Licensing & Distribution

| Attribute | Value |
|-----------|-------|
| **License** | Apache-2.0 (all sources) |
| **npm Package** | `@daytona/opencode` |
| **Fork on OpenDock** | `@veris-ai/daytona-opencode` (fork of `@daytona/opencode`, Copyright Daytona Platforms Inc.) |
| **Latest Version (OpenDock)** | 0.4.1 (published 2026-08-28) |
| **Maintenance Status** | Actively maintained (OpenDock) |

*Sources: daytona/integrations README, Goober-Codes/daytona-pi README, OpenDock plugin page*

---

## 7. Related Guides (Daytona Documentation)

The Daytona documentation portal lists three OpenCode guides:
1. **Run OpenCode with the Daytona Plugin** (this plugin)
2. **Build a Coding Agent Using OpenCode SDK and Daytona** — step-by-step autonomous agent construction
3. **Build a Coding Agent Using OpenCode Web and Daytona** — running OpenCode's web interface in Daytona sandboxes  
*Source: Daytona OpenCode Guides page*

---

## 8. Critical Observations & Gaps

| Observation | Evidence Basis |
|-------------|----------------|
| **Dual repository presence** | Plugin README appears in both `daytona/integrations` and `Goober-Codes/daytona-pi` with near-identical content; relationship between repos not explicitly documented in provided sources |
| **OpenDock fork** | `@veris-ai/daytona-opencode` is a fork with explicit SDK duplication warning; upstream relationship to `@daytona/opencode` noted but divergence details absent |
| **Snapshot-based sandbox creation** | Mentioned in daytona/integrations README ("Creating sandboxes from a snapshot") but no details provided in collected sources |
| **No transcript or video evidence** | All sources are documentation/markdown; no spoken/video content to verify runtime behavior |
| **Version discrepancy** | OpenDock lists v0.4.1 (2026-08-28); no version field visible in GitHub READMEs |

---

## 9. Conclusions

The Daytona OpenCode plugin is a mature, actively maintained integration that delivers on its core promise: transparent, secure sandboxing of OpenCode sessions with Git-backed synchronization and live preview capabilities. Installation is minimal (single config entry + API key), and the developer experience aims for "add plugin, use OpenCode as usual."

Key strengths:
- Strong isolation model (per-session sandboxes)
- Persistent state without manual management
- Git-native workflow for change review
- Zero-runtime-configuration after initial setup

Areas requiring further investigation (outside provided sources):
- Snapshot-based sandbox provisioning details
- Exact sandbox lifecycle hooks and cleanup guarantees
- Performance characteristics of Git sync at scale
- Compatibility matrix with OpenCode versions

---

*Report compiled exclusively from provided documentation sources. No video transcripts, runtime verification, or external research were used. All claims cite specific source documents.*