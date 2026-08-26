---
type: operations guide
title: Runtime, delivery, and prototype authority boundaries
description: Django runtime configuration, static/logging delivery, administration, and implemented versus target security controls.
tags: [operations, security, django, components]
openwiki:
  roles: [operations, integration, testing]
  change_kinds: [configuration, component-registration]
  source_paths: [config/settings.py, studio/components/menu_icon/menu_icon.py, studio/components/status_badge/status_badge.py, studio/tests.py]
  symbols: [COMPONENTS, MenuIcon, StatusBadge]
  test_paths: [studio/tests.py]
  invariants: [COMPONENTS.libraries imports menu_icon and status_badge registration modules during Django startup.]
  validation_commands: [.venv/bin/python manage.py test studio.tests.StudioJourneyTests.test_dashboard_explains_reference_use_case --verbosity 0]
---

# Runtime, delivery, and prototype authority boundaries

## Entrypoints and local delivery

`manage.py` is the management entrypoint. `config/wsgi.py` and `config/asgi.py` each set `DJANGO_SETTINGS_MODULE=config.settings` and create a Django application. Local setup is `pip install -r requirements.txt`, `npm install`, `npm run build:css`, `.venv/bin/python manage.py migrate`, then `.venv/bin/python manage.py runserver`.

SQLite lives at `BASE_DIR / "db.sqlite3"`. Django migrations define the schema, seeded reference catalog, discovery metadata, manifests, runtime traces, evaluations, and evidence records; see [`architecture/ontology.md`](../architecture/ontology.md). There are no background workers, queues, cache stores, or executable production source-integration services. The repository does contain a request-driven, deterministic synthetic sandbox runtime; its scope is documented in [`workflows/sandbox-runtime.md`](../workflows/sandbox-runtime.md).

## Configuration ownership and precedence

`config/settings.py` owns environment configuration:

| Setting | Default/meaning |
|---|---|
| `DJANGO_SECRET_KEY` | Falls back to a demo-only value; replace before deployment. |
| `DJANGO_DEBUG` | `true` by default; controls Django debug behavior and storage/log diagnostics. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated, defaults to `localhost,127.0.0.1`. |
| `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY` | Empty by default; live provider fallback credentials. |
| `GEMINI_MODEL`, `ANTHROPIC_MODEL` | Defaults `gemini-3.6-flash` and `claude-sonnet-5`. |
| `LOG_LEVEL` | `DEBUG` under debug, otherwise `INFO`, unless explicitly set. |

For a live provider, submitted form key overrides its environment key; an absent submitted model falls back to the settings model. The form model value is client-controlled and is not a model allowlist. Credentials are request-scoped to client construction and are neither persisted by models/services nor retained in the password input after HTMX completes. See [`integrations/model-providers.md`](../integrations/model-providers.md).

The checked-in `.env.example` has placeholders only. Never add actual keys to repository files, proposal fields, proof events, or logging.

### django-components startup registration

`COMPONENTS["libraries"]` in `config/settings.py` is the deterministic Django-startup registration list for `studio.components.menu_icon.menu_icon` and `studio.components.status_badge.status_badge`. Importing those modules executes their `@register(...)` decorators and makes the registered `menu_icon` and `status_badge` template tags available to the workspace. This is intentionally more than asset autodiscovery: `COMPONENTS["app_dirs"]` and the component finder still support component discovery/assets, but a long-running development server's autoreloader does not watch a Python component module that did not exist when it started. Adding a component module therefore must add its registration module to `libraries` (unless another explicit startup import exists), then restart or reload the development server so the changed settings take effect.

The [workspace guide](../web/workspace.md) owns the tag consumers and component contracts: `menu_icon` renders the six dashboard navigation glyphs, while `status_badge` renders controlled status/risk and ontology-state badges. The existing dashboard integration test verifies a dashboard HTTP 200 render through this settings-to-template path; it does not establish behavior beyond the rendered registrations.

**Change surface and focused check.** For a new reusable Python component, implement and register it in its module, add that exact module path to `COMPONENTS["libraries"]`, add/update its template consumers, and include component-template classes in Tailwind's configured sources where needed. Do not hand-edit generated CSS. Run `.venv/bin/python manage.py test studio.tests.StudioJourneyTests.test_dashboard_explains_reference_use_case --verbosity 0` to exercise the rendered dashboard; run `npm run build:css` only when CSS sources or component-template classes change. `collectstatic` remains conditional on a static-delivery change, not ordinary component registration.

## Static files and logging

`STATIC_ROOT` is `staticfiles`; static URLs use `static/`. WhiteNoise follows `SecurityMiddleware`: with `DEBUG`, `CompressedStaticFilesStorage`; without it, `CompressedManifestStaticFilesStorage`. For a production asset delivery, run:

```bash
npm run build:css
DJANGO_DEBUG=false .venv/bin/python manage.py collectstatic --noinput
```

The Tailwind source is `studio/assets/css/input.css`; generated `studio/static/studio/css/app.css` is what the template serves. The [institutional theme guide](../web/theme-system.md) documents the two-tier daisyUI palette and favicon source; change the source and rebuild rather than hand-editing generated CSS. `django-browser-reload` is installed and middleware-enabled; README documents its debug behavior.

`config.logging.configure_logging()` removes Loguru defaults, creates a readable stderr sink, forces standard logging through `InterceptHandler`, applies noisy-logger levels, and sets `backtrace`/`diagnose` from `DEBUG`. It formats Django server lines into method/target/status/size and labels known sources. This is terminal presentation, not an audit evidence pipeline; do not assume it redacts arbitrary application secrets.

## Authentication, authorization, and administration

Django session, authentication, CSRF, messages, and clickjacking middleware are installed. Admin is mounted at `/admin/`, so normal Django admin authentication applies there. The proposal endpoints are **public in this code**: `dashboard`, `compose_proposal`, `proposal_detail`, and `approve_proposal` have method decorators but no login or permission decorator. CSRF protection remains active for POSTs because the base template supplies the token/header.

Critically, the `user-entitlement-check` ontology control is **target-state metadata and a deterministic declaration check**, not implemented request-authenticated user-and-agent authorization. `_evaluate_controls()` can mark that control as present, while no workflow view derives an institutional user identity and `ApprovalForm.approver` accepts a submitted string rather than an authenticated principal. The synthetic sandbox does construct fixture human/agent identities and denies unbound or unentitled fixture calls, but that local behavior is not a production entitlement decision; see [`workflows/sandbox-runtime.md`](../workflows/sandbox-runtime.md). A passing proposal, approval, or sandbox run must not be interpreted as a production access grant or institutional separation-of-duties proof.

`studio/admin.py` exposes catalog/proposal records for inspection and maintenance. Nodes, edges, proposals, bindings, and checks remain mutable through normal `ModelAdmin` behavior; this can alter the reference catalog or proposal data. `ProofEventAdmin` has all fields read-only and refuses add/change/delete, preserving its UI append-only policy. The database model does not independently prohibit writes outside admin. `django-auditlog` tracks the governed domain models configured in `AUDITLOG_INCLUDE_TRACKING_MODELS`, including manifests, sandbox instances, tool invocations, evaluations, and evidence artifacts; `AUDITLOG_DISABLE_REMOTE_ADDR` avoids recording remote addresses and `AUDITLOG_CID_HEADER` uses `x-request-id` for correlation. `AuditTrailTests.test_authenticated_proposal_creation_is_audited_without_remote_address` proves an authenticated test client is recorded as actor while remote address is absent. No dedicated tests cover admin permissions or public-route authorization.

## Operational validation

- `.venv/bin/python manage.py check` — Django/settings validation.
- `.venv/bin/python manage.py migrate` — schema and reference-catalog application.
- `.venv/bin/python manage.py test` — dashboard and governed workflow integration tests.
- `npm run build:css` — regenerate CSS after source/template class changes.
- `DJANGO_DEBUG=false .venv/bin/python manage.py collectstatic --noinput` — production static collection check.

The scheduled wiki automation has a distinct write and secret boundary; see [`openwiki-automation.md`](openwiki-automation.md).
