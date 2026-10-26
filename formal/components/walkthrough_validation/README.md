# Walkthrough validation core

For a finite sequence of normalized steps and an exact rational budget of
`numerator / denominator` minutes, this core accepts exactly when the
denominator and numerator are positive, `numerator <= 10 * denominator`,
there are at least five steps, at least four distinct commands and at least
four distinct evidence references across them, and each step has a command,
an inspection reference and an evidence reference. `Evaluate` proves the
executable decision equivalent to that independent relation and returns the
exact distinct counts. Acceptance implies the stated positive ten-minute
bound; `OverBudgetCannotBeDeclared` rules out every budget above it.

The host keeps malformed declared steps as empty steps, treats non-list
reference fields as empty and discards blank strings. The adapter assigns
the remaining strings injective integer identities. It uses Python
`Fraction` to obtain the exact numerator and denominator of the observed JSON
integer or binary floating-point number; it does not reconstruct the original
decimal token. The host maps malformed or nonfinite budgets to zero before
the generated call, which rejects them, and reports the input diagnostic.
The direct component rejects nonnumeric budgets. Its default budget is ten
minutes; the production host always supplies the observed normalized budget.

The source-linked mutants separately remove the executable per-step evidence
check and the executable upper budget guard, preserving the specification.
Both must fail verification. Metadata binds their exact source replacements
and the generated Python inventory.

Numeric parsing, string normalization and identity injection, diagnostics,
the worker, Dafny/Boogie/Z3, compiler, generated runtime and Python remain
trusted. Declared optional step intervals and public-relative/localhost
reference boundaries receive separate host checks. Origin-relative browser
routes resolve only against an explicit loopback URL declared in the same
step; planned public files need not exist. The theorem proves the
declared budget bound, not elapsed execution time, that a command runs, that
planned output files already exist, or that a reference substantiates a claim.
