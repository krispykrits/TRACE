# Current trust boundaries

Core evidence and knowledge use cases accept trusted context separately from query filters. Source access, service/environment, freshness, withdrawal and saved citations are checked by the existing contracts/adapters. Retrieved text stays untrusted data; scores do not establish answerability or authority. See [package boundaries](../architecture/package-layout.md) and [production remediation scope](../planning/production-remediation-scope.md).

Current local contexts assume an authorized caller and controlled filesystem. They do not authenticate an operator, sandbox Python code or provide a multitenant network service. SQLite administration and corpus publication are trusted adapter operations, not investigator tools. The runtime wheel excludes evaluator labels and tests; fast architecture checks forbid runtime imports of them. Source/file access and prompt-injection resistance still require behavioral tests and review.

Before real-data or hosted use, document authenticated identity/grant derivation, least-privilege source/database/provider roles, redaction and permitted transmission, retention/deletion including derived vectors and backups, access-controlled audit ownership, and adversarial acceptance evidence. Changes to credentials, tool authority, persistence, export or source policy must include negative boundary tests. AI findings never constitute human endorsement or mutation approval.

The separately reviewed integrity, database-error and usage-redaction findings remain follow-up behavior changes; this folder refactor does not resolve them or establish production acceptance.
