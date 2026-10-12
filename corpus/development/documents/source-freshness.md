# Scope
Establish which log, metric and deployment sources are permitted for the service and window. A successful empty result, a failed query, a truncated result and an unavailable source are different outcomes.

# Time and provenance
Use observed event time for the incident timeline and retain collection time as provenance. Record source identity and revision. Delayed collection must not imply a later operational event. Query only within granted services, environment and access scope.

# Recheck
A saved citation must still resolve under current permissions and source freshness. If a source is withdrawn or no longer fresh, report that limitation and request an authorized revalidation. An old snapshot is not standing access permission.
