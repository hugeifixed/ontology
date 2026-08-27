# Governed Workflow Studio

This prototype shows how a plain-language business need can be matched to a governed catalog, turned into a reviewable agent specification, approved by accountable owners, and evaluated in a synthetic sandbox.

It is designed for product, management, architecture, and governance discussions. It runs locally with synthetic data and does not require an external model or API key.

## Start here

You do not need an API key, cloud account, or production data to run the demonstration. The default deterministic route is the recommended path for a first walkthrough.

### What you need

- Python 3.12 or newer
- Node.js with `npm`
- A terminal opened in this project directory

### Set up and start the application

Copy and run this block from the project directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
npm install
npm run build:css
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Keep the terminal open while using the application. Press `Control-C` in that terminal to stop it.

Expected startup result:

```text
System check identified no issues
Starting development server at http://127.0.0.1:8000/
```

If port 8000 is already occupied, run the application on another port:

```bash
.venv/bin/python manage.py runserver 8001
```

Then open <http://127.0.0.1:8001/>.

### Ask an LLM coding assistant to set it up

If you prefer, open this repository in a coding assistant and paste the following prompt:

```text
Set up and run this Django demonstration locally. Read AGENTS.md and README.md first.
Use the deterministic demo provider; no API key is needed. Do not add, print, or commit
secrets. Do not edit or regenerate the openwiki folder. Create the virtual environment,
install Python and npm dependencies, build CSS, apply migrations, run Django checks and
tests, then start the development server. If port 8000 is occupied, choose the next free
local port. Tell me the URL to open and explain any failure in plain language.
```

The assistant should finish by reporting the local URL and the results of `manage.py check` and `manage.py test`.

### Common setup issues

- **`python3` or `npm` is not found** — install an approved Python 3.12+ and Node.js distribution, then reopen the terminal.
- **Port already in use** — use `runserver 8001` as shown above. Do not repeatedly start more servers.
- **A Python package is missing** — rerun `.venv/bin/pip install -r requirements.txt`; make sure commands use `.venv/bin/python`, not a different Python installation.
- **The interface looks unstyled** — run `npm install` and `npm run build:css`, then refresh the browser.
- **A live model is slow or unavailable** — switch back to **Deterministic demo**. The walkthrough does not require an external provider.
- **Database tables are missing** — run `.venv/bin/python manage.py migrate`.

## Eight-minute guided walkthrough

1. Open **Home**. Establish the boundary: this is a governed sandbox design exercise using synthetic data, not a production deployment.
2. Open **Start review**. The commercial-loan insurance example is already loaded.
3. Select **Discover catalog path**. Review the matched workflow, source products, registered agent, capability, owners, and typed relationships.
4. Select **Use this catalog path**. The discovered intent is copied into the runnable reference case.
5. Keep **Deterministic demo** selected and choose **Draft and open proposal**. This route is fast, repeatable, and requires no key. The proposal opens in its own refresh-safe workspace.
6. Use the proposal stages:
   - **Define** — inspect the outcome, deterministic policy checks, and connected catalog objects.
   - **Approve** — download the versioned manifest and record separate business-owner and source-owner approvals.
   - **Test** — register the mocked agent, then run the synthetic evaluation.
   - **Evidence** — confirm the sandbox gate, citations, access denial, evaluation results, latency, cost, hashes, and downloadable JSON evidence.
7. Finish at **Sandbox evaluation passed**. Do not describe the result as production approval.
8. If time remains, compare **Browse catalog** and **Relationship map** under **Knowledge model**, then open **System connections** to discuss which responsibilities belong to the institution and which belong to a future platform integration.

What the walkthrough should make clear:

- Semantic discovery ranks likely catalog objects; typed ontology relationships establish the actual dependency path.
- An LLM may interpret intent, but application code validates references and controls.
- Humans authorize sandbox use; the LLM does not approve or create production access.
- The runtime uses governed tools and separate human and agent identities rather than direct database or file-share credentials.
- Evidence demonstrates what happened. It does not imply production readiness.

Useful terms:

- **Ontology** — the governed catalog of concepts and their typed relationships.
- **Agent manifest** — the exact versioned specification approved for sandbox registration.
- **Sandbox** — an isolated synthetic execution used to test behavior and controls.
- **Evidence artifact** — a hashed JSON record supporting review and audit.

## Information architecture

The interface is organized around user tasks instead of implementation layers:

- **Home** shows the five-stage path, work to resume, and the next accountable action.
- **Start review** progressively reveals discovery, request definition, and proposal drafting.
- **Proposals** is the task list. Search and filter by status, risk, or next accountable role.
- **Knowledge model** combines catalog browsing and typed relationship tracing without treating them as separate systems.
- **System connections** explains model, source, control, and evidence boundaries. It is reference information, not a workflow step.
- Workspace search returns catalog objects, proposals, and evidence findings in separate result groups.

Each proposal has one canonical URL, such as `/proposals/9?stage=approve`. The `stage` query parameter preserves **Define**, **Approve**, **Test**, or **Evidence** across refreshes and shared links. The interface recommends one next action and names the role expected to perform it. Older dashboard links using `overview`, `compose`, `catalog`, or `ontology` remain compatible and open the corresponding new section.

The current structure should still be validated with representative users. Use short tree-testing tasks such as “find the source owner’s approval queue,” “trace what the insurance workflow reads,” and “return to the evidence for a completed review.” Capture wrong turns and completion time before adding more navigation or agent types.

## Cross-domain discovery

The Start review screen performs explainable semantic discovery across treasury management, retail banking, and commercial loan servicing. It first applies a simulated domain-and-classification access profile, expands recognizable business concepts, ranks approved catalog metadata, and follows typed ontology relationships from a workflow to its data products, agent instance, and inherited capabilities.

This small catalog does not need another vector database. The matcher is deterministic and inspectable: its curated search terms and domain concepts are stored alongside catalog metadata, while the graph supplies authoritative dependency paths. A weak match becomes a metadata gap instead of being forced into an unrelated workflow. Only the commercial-loan result can continue to the synthetic runtime; treasury and retail results intentionally stop at discovery because their runnable adapters are not implemented.

## Reference workflow

1. A business user states an insurance-review outcome and operational boundaries.
2. An optional LLM connector interprets the intent into a Pydantic-validated proposal using approved catalog metadata only.
3. Django resolves every ontology reference, rejects invented assets, runs deterministic controls, and exports an exact, versioned agent manifest.
4. A business owner and a source owner independently approve the sandbox specification.
5. A mocked orchestration API registers a sandbox agent instance from the approved manifest.
6. The sandbox invokes three deterministic tools while carrying separate human and agent identities through every call.
7. The policy path records allowed access and an entitlement denial without returning denied source content.
8. The review returns findings with document, page, section, and excerpt citations from synthetic documents.
9. Four evaluations test citation accuracy, refusal, access control, and prompt-injection handling.
10. The evidence report records the model route, prompt version, token use, estimated model cost, latency, approvals, policy decisions, tool-call hashes, findings, evaluation results, and artifact hashes.

The terminal state is **Sandbox evaluation passed**. The prototype uses synthetic source data and a mocked orchestrator. It does not connect to production sources, create real entitlements, store provider keys or raw model responses, deploy an agent, or imply production approval.

## Optional model providers

For local development, copy `.env.example` to the git-ignored `.env` file and set the provider values there:

```bash
GOOGLE_API_KEY="..."
ANTHROPIC_API_KEY="..."
```

`GOOGLE_API_KEY` configures the Gemini Developer API with a Google AI Studio key. You can instead enter a replacement key on the Start review screen. By default, the server uses it to construct one provider client for that request and then clears the browser field. It does not write the key or raw provider errors to SQLite, logs, Django sessions, or proof events.

For a workshop, the user can explicitly select **Reuse in this browser tab**. That opt-in stores a provider-specific key in browser `sessionStorage`, restores it for later submissions in the same tab, and removes it when the user unchecks the option or closes the tab. The git-ignored `.env` file remains the recommended local setup; an enterprise model gateway with managed identity is the production direction. Process environment variables take precedence over `.env` values.

Gemini requests use a 30-second per-attempt timeout and retry transient timeouts, rate limits, and server failures once, for two total attempts. This gives an interactive request an approximate one-minute ceiling. Invalid credentials and unavailable model names are not retried.

Defaults:

- Gemini: `gemini-flash-latest`
- Anthropic: `claude-sonnet-5`

Override them with `GEMINI_MODEL` or `ANTHROPIC_MODEL`. The Anthropic connector accepts
current first-party Claude API model IDs, including `claude-opus-5`; enter one in the
Model route field or set `ANTHROPIC_MODEL=claude-opus-5`.

Anthropic requests use the SDK's structured-output parser, a 30-second per-attempt timeout,
and one automatic retry for connection failures, rate limits, and transient server errors.

## Explore the project with OpenWiki

The generated [`openwiki/`](openwiki/) directory provides an architecture-oriented view of the repository. It connects the catalog, ontology, proposal lifecycle, sandbox runtime, integrations, and operations documentation. Source code and tests remain authoritative.

Install the same OpenWiki CLI version used by the automated documentation workflow:

```bash
npm install --global openwiki@0.3.3
```

From the project root, open the interactive relationship graph and documentation reader:

```bash
openwiki visualize openwiki
```

The command opens a browser automatically and serves the viewer on port `4321`. If that port is occupied, OpenWiki selects the next available port. To choose a port and start the viewer without opening a browser, run:

```bash
openwiki visualize openwiki --port 4400 --no-open
```

Then open <http://127.0.0.1:4400/>. Press `Control-C` in the terminal to stop the viewer.

After meaningful code or source-documentation changes, regenerate the repository documentation with:

```bash
openwiki code --update --print
```

An update may require configured provider authentication and can take several minutes. Review generated changes before committing them. Prefer changing source code or source documentation and regenerating the wiki instead of manually editing generated OpenWiki pages. The repository also includes a scheduled and manually dispatchable GitHub Actions workflow at [`.github/workflows/openwiki-update.yml`](.github/workflows/openwiki-update.yml).

## Test

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test
```

Install the development tools and run Ruff linting and formatting checks with:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

## Accessibility

The interface targets WCAG 2.2 Level AA. It has semantic landmarks and tables, explicit form labels, visible keyboard focus, a skip link, text alternatives for visual status, asynchronous update announcements, 24-by-24-pixel minimum targets, responsive reflow, and reduced-motion support. Before production, test it manually with a keyboard, screen reader, browser zoom, and contrast tools.

## Technical stack

The application uses Django 5.2, SQLite, daisyUI 5, Tailwind CSS 4, django-components, django-htmx, django-template-partials, Alpine.js, WhiteNoise, django-auditlog, Pydantic, and Loguru. The implementation began from the concepts in `../catalog_wireframe_v3.html`.

## Project shape

```text
config/                   Django settings and root routing
studio/models.py          Ontology, proposal, review, runtime, evaluation, and evidence records
studio/discovery.py       Hard filters, semantic concept matching, and typed graph expansion
studio/types.py           Frozen Pydantic provider contracts
studio/services.py        Intent composition and deterministic proposal validation
studio/sandbox_services.py Manifest, approvals, orchestration, evaluation, and evidence
studio/sandbox_runtime.py Synthetic tools, identities, policy, documents, and findings
studio/orchestration.py   Deterministic mocked orchestration adapter
studio/providers/         Demo, Gemini, and Anthropic adapters
studio/components/        Reusable server-rendered UI components
studio/views.py           Thin HTML/HTMX entry points
studio/templates/         daisyUI and Alpine presentation
  studio/partials/        Task sections and the canonical proposal workspace
studio/static/            Tailwind input/output and small browser behavior
docs/architecture.md      Control boundaries and workshop discussion points
```

## Before production

- Replace direct API keys with an enterprise model gateway and managed identities.
- Integrate institutional IAM and source-level authorization.
- Replace the mocked orchestration adapter and synthetic tools with approved runtime and source connectors after validating their contracts.
- Add an external API only after a concrete client, authorization model, and versioned contract exist; the current HTML/HTMX journey does not require GraphQL.
- Add immutable external evidence storage and retention policy.
- Expand the evaluation pack, threat model, provider-cost mappings, failure-mode tests, and promotion controls.
- Replace synthetic ontology entries with governed records owned by institutional teams.
