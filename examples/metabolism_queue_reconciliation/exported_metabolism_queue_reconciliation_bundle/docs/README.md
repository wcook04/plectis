# Metabolism Queue Reconciliation - exported bundle

This bundle accompanies the `metabolism_queue_reconciliation` organ. The organ surfaces the public `metabolism_runtime` engine-room capsule as a first-class runtime.

## What the mechanism does

A small, runnable model of a durable job queue. It puts jobs in a temporary scratch database, hands one out to a worker on a lease, recovers the job when the lease expires, and tracks claim-and-contradiction events on a shared blackboard. It then runs a consistency check that flags impossible situations for a human to review, for example a job marked "running" with no record of a run, or a run that finished while its job still says running. Two clean scenarios are checked end to end; two deliberately broken scenarios are confirmed to be caught and rejected. It is a faithful but bounded copy of the real machinery: it never touches the live production database, never starts agents, and never silently fixes anything.

## What it does not claim

Real-substrate capsule run over public fixtures; status pass attests only that the synthetic queue/reconciliation computation behaved as specified on these bounded cases. Does NOT export the live private metabolism database/scheduler, does NOT dispatch agents, does NOT call providers, does NOT auto-repair ambiguous runtime state, is NOT a distributed database, is NOT an oracle/prover, and does NOT authorize release, publication, production use, or source mutation.

## Fixture cases

queue_lease_recovery_ok (positive): enqueue twice under one idempotency key (second blocked), claim a job, let the lease expire, recover it to recoverable, and confirm a fresh reconcile stays healthy.
blackboard_projection_ok (positive): assert one blackboard claim then contradict it; the active-claim projection drops to zero active claims with one recorded contradiction.
running_job_no_run_row_rejected (negative): a job forced into running with no run row; the reconciler must reject the store by firing rule running_job_no_run_row (needs_review).
finalized_run_running_job_rejected (negative): a run finalized with completed_at while its job is still running; the reconciler must reject by firing rule run_finalized_but_job_running (needs_review).

## Run it

```bash
python -m microcosm_core.organs.metabolism_queue_reconciliation run \
  --input fixtures/first_wave/metabolism_queue_reconciliation/input \
  --out receipts/first_wave/metabolism_queue_reconciliation
```
