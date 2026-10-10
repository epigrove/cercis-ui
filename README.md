# cercis-ui (plugin UI specification)

**English** | [中文](README.zh-CN.md)

> May Cerces safeguard your thoughts.

The **plugin UI specification** for Cercis, plus its tooling. It answers one question:
**how can the same plugin UI run from one piece of code on Mac, Windows, Linux and phones, while
still looking like each system?**

The answer is not "translate a web page into native widgets", it is:

```
plugin author's HTML draft  ──compiler──▶  UI blueprint (JSON)  ──renderer──▶  native UI per platform
        pleasant to write                   machine-readable                    looks native to users
```

## What is in this repository

| Directory | Content |
|-----------|---------|
| `spec/` | **the specification** + the blueprint format (JSON Schema) + official examples |
| `tools/` | validator: checks a blueprint against the schema (zero dependencies, Python stdlib only) |
| `compiler/` | compiler: HTML draft → blueprint (*planned*) |
| `renderers/` | per-platform "build from the blueprint" programs: web / macOS / Windows / Linux / Android / iOS (*planned*) |
| `conformance/` | conformance testing: feed one blueprint to every renderer; structure and actions must match (*planned*) |

## Who uses it

| Role | How |
|------|-----|
| **Plugin authors** (official or third-party) | write an HTML draft per `spec/v1.md`, compile it into a blueprint, hand it to the app |
| **App developers** | render the blueprint with that platform's native controls; own permissions, fallbacks and error messages |
| **The kernel** | knows nothing about UI; it only relays "which interfaces this plugin offers" in the manifest |

The boundary in one line: **plugins describe the UI, they do not draw it; the app draws the UI, it
does not implement business logic.**

## Three paths (plugins choose)

1. **Declarative** (recommended): write a blueprint → works everywhere, same structure, controls
   follow the platform
2. **Platform-native snippets**: hand-written native UI for one platform (for third parties
   chasing the last 10% of polish)
3. **WebView fallback**: complex visualisations, print previews and the like stay a web page
   inside a sandboxed browser view

A plugin declares which path it takes and which platforms it supports; unsupported platforms hide
the entry point and nothing else breaks.

## Where to start

1. [specification v1](spec/v1.md) — which building blocks exist, how to arrange them, how to bind data
2. [two real examples](spec/examples/) — an import-CSV wizard and a health report (HTML draft + blueprint each)
3. [blueprint format](spec/schema.json) — for machine validation

## Try it now

```bash
# validate the example blueprints (a broken file tells you which line is wrong)
python3 tools/validate.py spec/examples/*.json

# sample output:
# ✓ spec/examples/import-csv.json passed (13 components)
# ✓ spec/examples/health-report.json passed (10 components)
```

## Status

**v1 draft**: the specification, the blueprint format, the validator and two examples are in place.

Next, in order:

1. **Compiler**: `cercis-ui compile import-csv.html -o import-csv.json` (HTML draft → blueprint)
2. **Web renderer**: let today's desktop app render blueprints directly (replacing hand-written buttons)
3. **macOS native renderer**: prove that "one blueprint → native controls" really works
4. **Conformance**: every renderer produces the same "structural snapshot" for the same blueprint

## License

Apache-2.0 (see `LICENSE`). The specification text is free to quote and implement (including by
third-party renderers).
