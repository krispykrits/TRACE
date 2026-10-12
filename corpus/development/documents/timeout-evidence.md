# Scope
A timeout reports a caller-visible deadline failure. It does not identify which dependency or configuration caused the delay. Record service, environment, incident window and the authorized evidence sources before investigating.

# Evidence checks
Compare caller failures with Payment request durations and dependency spans from the same authorized window. Check deployment/configuration history, timestamps, effective timeout configuration and work duration separately. Preserve exact error codes such as HTTP 504 and /v1/orders without rewriting them. A nearby deployment can be unrelated.

# Missing evidence
Report capture gaps and collection delay. If configuration or downstream duration cannot be observed, retain competing explanations and propose a specific source check. Do not guess a cause from a symptom or from the absence of logs. Suggested checks do not authorize a configuration change.
