# Derived Fact Provider Runtime - exported bundle

This bundle accompanies the `derived_fact_provider_runtime` organ. The organ surfaces the public `derived_fact_provider_engine` engine-room capsule as a first-class runtime.

## What the mechanism does

A small engine that fills in facts from a list of recipes. Each recipe says where a number or string lives — pull this field out of a JSON file by its path, count the files matching this pattern, or run a named helper like "how many tracked files are there". When a recipe points at something that is not there, the engine does not fall over: it writes that fact down as an error with a hint about how to fix it, and marks the overall run as degraded. The organ checks two well-formed recipe lists resolve to the right answers, and two broken ones (a missing file, an unknown recipe type) get caught and reported as errors rather than slipping through. It only resolves facts against the files you give it; it does not decide whether any larger claim is true.

## What it does not claim

A pass means the surfaced fact-provider capsule resolved the authored fixture registries against their supplied roots and rejected the planted-defect registries by recomputation with the expected error_class. It does NOT mean any downstream prose claim is true (not a doctrine truth auditor), does NOT cover the full macro fact registry (not a full export), does NOT perform semantic claim validation, does NOT prove the provider correct beyond the bounded fixtures, and grants NO release, publication, private-source-export, or source-mutation authority. The only runtime variability admitted is filesystem reads, the git subprocess used by callable facts (over isolated tempdirs), and CLI argument reads.

## Fixture cases

json_pointer_glob_clean (positive): a clean registry resolving an integer via JSON pointer /summary/fact_count and a markdown file count via glob docs/*.md with private/ excluded; expects value 7 and 2 and an ok receipt.
git_callable_and_pointer_index_clean (positive): exercises the git-backed callable facts (git_tracked_file_count=2, git_tracked_python_count=1) over a tempdir git index plus an RFC 6901 list-index pointer /entries/1 -> 'beta'; expects an ok receipt.
missing_source_path_rejected (negative): a json_pointer provider pointing at an absent source_path; the capsule records an error-as-data row with error_class FileNotFoundError and degrades the receipt, which the runner asserts.
unknown_provider_type_rejected (negative): a registry naming an unsupported provider_type 'imaginary_provider'; the capsule records an error-as-data row with error_class ValueError and degrades the receipt, which the runner asserts.

## Run it

```bash
python -m microcosm_core.organs.derived_fact_provider_runtime run \
  --input fixtures/first_wave/derived_fact_provider_runtime/input \
  --out receipts/first_wave/derived_fact_provider_runtime
```
