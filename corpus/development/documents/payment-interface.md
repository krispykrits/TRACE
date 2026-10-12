# Boundary
The Payment development fixture receives an order ID and positive amount. The work result and the caller's configured deadline are separate observations. The fixture makes no real charge.

# Evidence vocabulary
Useful evidence can include request failures, measured work duration, effective caller budget and configuration revisions. Keep each source's record identity, version, service, environment and observed time when joining a request timeline. HTTP 504 is a symptom code, not a root-cause label.

# Interpretation
A hypothesis must account for supporting evidence and alternatives. An unchanged budget with slower observed work calls for different checks than a changed budget with stable work. Missing evidence can make these hypotheses indistinguishable; disclose the gap rather than assigning a causal probability.
