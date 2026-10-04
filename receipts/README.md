# Recorded results

These files record outputs from component checks, demonstrations and repository
validation. They let you inspect what a particular run reported without
rerunning it. They describe their recorded inputs and scope, not the current
state of your machine.

To produce a new result, start with a [worked example](../examples/README.md).
Keep your output under the ignored `.microcosm/` directory instead of replacing
the checked-in records here.

## Start with a result you can explain

| Recorded result | What to inspect | How to rerun it |
| --- | --- | --- |
| [Agent completion audit](first_wave/agent_closeout_faithfulness_audit/agent_closeout_faithfulness_audit_result.json) | Verified claims, the actual pytest exit status, and deliberately incorrect claims that were rejected | [Checking agent completion](../docs/guides/checking-agent-completion.md) |
| [Prompt-injection check](first_wave/indirect_prompt_injection_information_flow_policy_replay/indirect_prompt_injection_information_flow_policy_replay_result.json) | Which supplied sources may carry instructions, and which rule rejects an altered input | [Prompt-injection walkthrough](../docs/guides/prompt-injection.md) |

The saved completion audit dates from 31 May 2026. It records three negative
cases and has no `negative_case_semantics` field. The current guide describes
the newer runner, which checks four negative cases and writes that field.
Following the guide produces a new result from your checkout's version;
compare the checks and inputs rather than expecting an identical JSON file.

Begin with the input and command, then read the status and findings. For the
completion audit, `status: pass` means the valid claims verified and the
expected false claims were rejected. Its `error_codes` include those expected
rejections; their presence alone does not mean the whole run failed.

Compare a result with its [inputs](../fixtures/README.md) and implementation
tests. A recorded `pass` establishes the stated check on those inputs; it is
not a general quality score or evidence that you reproduced the run yourself.

## Find the right kind of record

- [`first_wave/`](first_wave/) and [`second_wave/`](second_wave/) contain component
  results, summary boards and validation records.
- [`runtime_shell/`](runtime_shell/) contains results from the local project
  demonstration and its component runs.
- [`code_lens/`](code_lens/) contains generated navigation data and reading
  packets used by the comprehension commands.
- [`preflight/`](preflight/) contains repository and dependency checks.
- [`release/`](release/) contains recorded packaging and review checks.

Other directories support specific import, documentation and validation tasks.
Use the [component map](../ORGANS.md#find-your-specialty) to select a component
and follow its recorded input and output paths.

## Inspect your own run

After running an example, open the result path printed by its command. For the
completion guide, the saved file can be formatted with:

```sh
python -m json.tool \
  .microcosm/examples/agent-completion/agent_closeout_faithfulness_audit_result.json
```

Keep the command, inputs and source version with the result when sharing it.
The [validation guide](../docs/maintainers/validation.md#open-saved-result-files)
also describes listing and inspecting project-local outputs.

## Updating recorded results

When a contribution changes a component, run its tests and regenerate only its
owned records with the documented runner. Do not hand-edit a saved JSON result
to make it agree with new inputs. See [contribution guidance](../CONTRIBUTING.md)
and the [validation guide](../docs/maintainers/validation.md) for the appropriate
checks.

Return to the [documentation index](../docs/README.md) for explanations and guides.
