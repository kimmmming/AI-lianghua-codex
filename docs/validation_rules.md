# Validation Rules

Every selection run must validate:

- unique security identifiers;
- valid trading dates;
- no duplicated financial records;
- financial `announcement_date` is not after `as_of_date`;
- factor coverage and missing rates;
- industry minimum and maximum constraints;
- deterministic output for identical inputs and configuration.

Stage 1 provides test skeletons only. Full validation logic will be implemented after data schemas are finalized.
