# Worked guides

Choose one example, run it and trace the result back to its input and code.
Each guide explains what its check establishes and shows where it stops.
Start with the [quickstart](../../QUICKSTART.md) if you have not cloned the
repository; read the [project overview](../overview.md) for the wider purpose.

| Guide | What you do | Requirements beyond the clone |
|---|---|---|
| [Check an agent's completion claims](checking-agent-completion.md) | Create a sample Git repository, run real tests and compare claims about commits, files and test results with what happened. | Python 3.11+, Git and pytest; setup is included. |
| [Change a prompt-injection example](prompt-injection.md) | Inspect a saved record, run its checker and change a permission field to make a check fail. | Python 3.11+; no model account. |
| [Prepare a question for an expert](hypothesis-handoffs.md) | Write down a question, possible answers and observations that could distinguish them; validate the file. | Python 3.11+; no model account. |

For a first example of a check against actual commands, choose completion
claims. For a smaller input you can edit and understand in one sitting, choose
prompt injection. For planning a research conversation, choose the expert
question guide.

## Find more examples

The [examples directory](../../examples/README.md) explains the supplied input
folders. The [component map](../../ORGANS.md) lists all components, their
commands and their stated limits. Some examples run computations or external
tools; others check prepared records. Read the selected component's
requirements before running it.

Save new output under the ignored `.microcosm/` directory. The committed
[recorded results](../../receipts/README.md) document earlier runs;
[fixtures](../../fixtures/README.md) supply cases for repeatable tests.

Return to the [documentation index](../README.md), or see the
[maintainer guides](../maintainers/README.md) when you are ready to change code.
