# Maintainer guides

Start with [Contributing](../../CONTRIBUTING.md) for reporting a problem or
proposing a change. These guides explain how to change the toolkit and check
that it still works as an independent repository and installed package.

| Task | Guide |
|---|---|
| Find the implementation or add a command | [Architecture and implementation map](architecture.md#implementation-map) |
| Edit a generated document or move a file | [Document owners](architecture.md#keep-each-document-in-its-role) and [producers and consumers](architecture.md#change-producers-and-consumers-together) |
| Run tests, examples or a standalone export | [Validation](validation.md) |
| Check source and publication boundaries | [Public boundary](../governance/public-boundary.md) |
| Prepare a release and interpret its checks | [Release discipline](../governance/release-discipline.md) |
| Run security checks or report a concern | [Security runbook](security-runbook.md) and [reporting policy](../../SECURITY.md) |
| Work on the toolkit paper | [Paper source and build instructions](../../paper/README.md) |

## A typical change

1. Find the component in the [component map](../../ORGANS.md), then inspect its
   implementation, example input and tests.
2. Make the change and run the relevant focused tests. Use `make check` for the
   fast registry and source checks.
3. Regenerate affected documents through their named builder. If you move a
   file, update its imports, links, export rules and package data together.
4. Run `make ci` before proposing the integrated change. It includes command
   smoke tests and a fresh package installation; it may need network access.

The [validation guide](validation.md) has commands for narrower checks and
recorded release runs. Keep newly generated example output under `.microcosm/`
so it stays separate from source and committed result history.

Return to the [documentation index](../README.md).
