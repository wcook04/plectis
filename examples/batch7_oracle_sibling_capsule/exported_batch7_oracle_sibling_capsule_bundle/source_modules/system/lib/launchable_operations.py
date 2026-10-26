"""
[PURPOSE]
- Teleology: Centralize the SAFE launchable operation catalog plus parameter
  validation, command rendering, and meta-mission bookkeeping so the browser's
  manual hand and the reaction engine's automatic hand share one allowlist.
- Mechanism: Store the catalog as data, publish compact operation payloads for
  the UI, validate parameterized commands against a narrow schema, and expose
  helpers for launcher-owned meta-mission run bookkeeping.

[INTERFACE]
- Exports catalog/list/find, validate_and_render_command, prepare_launch_operation, meta-mission start/finalize/env helpers, and operation-output artifact/event extractors.
- PreparedLaunch carries the validated argv and launcher metadata.

[FLOW]
- Mechanism: Resolve allowlisted operation and parameters, apply dispatch ceilings, render argv, then optionally create/finalize meta-mission workspace receipts and extract output references.

[DEPENDENCIES]
- meta_mission_workspace owns run bookkeeping; dispatch_policy enforces wave ceilings; observe_mission_templates supplies authored templates; hologram_build_status and metabolism_policy inform operation options.

[CONSTRAINTS]
- Writes: Meta-mission helpers create/finalize run workspace state; preparation itself does not execute the rendered command.
- Fails: Unknown operations and invalid parameters return validation errors.
- Guarantee: Commands are rendered from catalog schemas rather than accepted as arbitrary launcher text.
"""
from __future__ import annotations

import json
import os
import re
import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from system.lib import meta_mission_workspace as _mmw
from system.lib.dispatch_policy import resolve_dispatch_policy, summarize_dispatch_policy
from system.lib.hologram_build_status import load_hologram_build_status
from system.lib.metabolism_policy import NVIDIA_CONTINUOUS_SOURCE_ORDER
from system.lib.observe_mission_templates import load_mission_template

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHABLE_PARAM_VALUE_RE = re.compile(r"^[A-Za-z0-9_./-]+$")

_BASE_CATALOG_JSON = r"""
[
  {
    "operation_id": "kernel_pulse",
    "label": "Kernel pulse",
    "kicker": "pulse",
    "description_short": "Single-shot kernel pulse: reports active phase, gate, routing emphasis.",
    "command": "python3 kernel.py --pulse",
    "parameters_schema": {},
    "principle_refs": [
      "pri_058",
      "pri_104"
    ]
  },
  {
    "operation_id": "kernel_info",
    "label": "Kernel info",
    "kicker": "info",
    "description_short": "Top-level kernel info packet: command groups, recent frontier, sources.",
    "command": "python3 kernel.py --info",
    "parameters_schema": {},
    "principle_refs": [
      "pri_086"
    ]
  },
  {
    "operation_id": "kernel_observe_status",
    "label": "Observe status",
    "kicker": "observe",
    "description_short": "Latest grouped-observe runtime status snapshot for the operator surface.",
    "command": "python3 kernel.py --observe-status latest",
    "parameters_schema": {},
    "principle_refs": [
      "pri_058"
    ]
  },
  {
    "operation_id": "kernel_build_status",
    "label": "Build status",
    "kicker": "build",
    "description_short": "Per-phase hologram staleness check without triggering a rebuild.",
    "command": "python3 kernel.py --build status",
    "parameters_schema": {},
    "principle_refs": [
      "pri_058"
    ]
  },
  {
    "operation_id": "kernel_embed_refresh",
    "label": "Embed refresh",
    "kicker": "embeddings",
    "description_short": "Refresh one embedding substrate source kind or all of them.",
    "command": "python3 kernel.py --embed-refresh {source}",
    "parameters_schema": {
      "source": {
        "type": "string",
        "required": false,
        "default": "all",
        "description": "Embedding source kind or 'all'."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_104"
    ]
  },
  {
    "operation_id": "navigator_refresh",
    "label": "Navigator refresh",
    "kicker": "navigation",
    "description_short": "Metabolism-facing navigation refresh: refresh stale embeddings for one source kind.",
    "command": "python3 kernel.py --embed-refresh {kind}",
    "parameters_schema": {
      "kind": {
        "type": "string",
        "required": false,
        "default": "all",
        "description": "Embedding source kind or 'all'."
      }
    },
    "ui_group": "navigation",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_086",
      "pri_104",
      "pri_111"
    ]
  },
  {
    "operation_id": "overnight_embed_refresh_launch",
    "label": "Overnight embed refresh",
    "kicker": "embeddings",
    "description_short": "Run the backend embedding freshness chain: source-watch scan, stale-source enqueue, bounded queue drain, and route_status finalizer.",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --chain overnight_embed_refresh --family {family} --provider {provider}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Compatibility parameter for the chain runner; embedding refresh itself is repo-wide."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "nim",
        "label": "Provider",
        "description": "Compatibility parameter for the chain runner; embeddings use the configured NIM lane."
      }
    },
    "ui_group": "navigation",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_086",
      "pri_104",
      "pri_125",
      "pri_142"
    ],
    "meta_mission_id": "overnight_embed_refresh",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "semantic_route_refresh",
    "label": "Semantic route refresh",
    "kicker": "routes",
    "description_short": "Refresh the derived semantic-routing plane and any stale embeddings needed for the requested source kind.",
    "command": "python3 kernel.py --route-refresh {source}",
    "parameters_schema": {
      "source": {
        "type": "string",
        "required": false,
        "default": "all",
        "description": "Semantic-routing source kind or 'all'."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_104",
      "pri_111"
    ]
  },
  {
    "operation_id": "semantic_route_quality_audit",
    "label": "Semantic route quality audit (Kimi K2)",
    "kicker": "routes",
    "description_short": "Audit drifted edges in the semantic routing plane via Kimi K2-thinking on NVIDIA NIM; emit append-only evidence rows (never mutates the graph). Signal-gated: only fires when the drift snapshot has actually changed since last cycle.",
    "command": "./repo-python tools/meta/control/semantic_route_quality_audit.py --sample {sample} --model {model}",
    "parameters_schema": {
      "sample": {
        "type": "integer",
        "required": false,
        "default": 8,
        "description": "How many drift-pressured nodes to audit per cycle."
      },
      "model": {
        "type": "string",
        "required": false,
        "default": "kimi-k2-thinking",
        "description": "NVIDIA NIM chat-model alias (kimi-k2.6, kimi-k2-thinking, kimi-k2.5, kimi-k2-instruct)."
      }
    },
    "principle_refs": [
      "pri_003",
      "pri_049",
      "pri_097",
      "pri_111"
    ]
  },
  {
    "operation_id": "nvidia_continuous_navigation_populate",
    "label": "NVIDIA continuous navigation populate",
    "kicker": "navigation",
    "description_short": "Run one guarded NVIDIA NIM embedding-population batch over stale navigation sources, with compact daemon logs and route refresh.",
    "command": "./repo-python tools/meta/control/nvidia_runtime.py run --batch-id {batch_id} --sources {source_kinds} --max-sources {max_sources} --limit-per-source {limit_per_source} --refresh-routes",
    "parameters_schema": {
      "batch_id": {
        "type": "string",
        "required": false,
        "default": "continuous_navigation",
        "description": "NVIDIA runtime batch id."
      },
      "source_kinds": {
        "type": "string",
        "required": false,
        "default": "raw_seed_shards,standards_json,python_holographic,raw_seed_paragraphs,raw_seed_navigation,paper_modules,skills,doctrine,archaeology_shards,annex_notes",
        "pattern": "^[A-Za-z0-9_,./-]+$",
        "description": "Comma-separated embedding source kinds."
      },
      "max_sources": {
        "type": "integer",
        "required": false,
        "default": 3,
        "minimum": 1,
        "maximum": 10,
        "description": "How many queued source kinds one batch may consume."
      },
      "limit_per_source": {
        "type": "integer",
        "required": false,
        "default": 25,
        "minimum": 1,
        "maximum": 200,
        "description": "Maximum source items to refresh per selected source kind."
      }
    },
    "ui_group": "navigation",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_086",
      "pri_104",
      "pri_111"
    ]
  },
  {
    "operation_id": "openrouter_free_model_probe",
    "label": "OpenRouter free-model probe",
    "kicker": "providers",
    "description_short": "Probe current OpenRouter free-model metadata, key quota posture, and no-spend throughput envelope.",
    "command": "./repo-python tools/meta/control/openrouter_free_runtime.py probe --top {top} --write",
    "parameters_schema": {
      "top": {
        "type": "integer",
        "required": false,
        "default": 20,
        "minimum": 1,
        "maximum": 100,
        "description": "Number of ranked free models to include."
      }
    },
    "ui_group": "providers",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_086",
      "pri_104"
    ]
  },
  {
    "operation_id": "openrouter_chat_smoke",
    "label": "OpenRouter paid chat smoke",
    "kicker": "providers",
    "description_short": "Run one tiny bounded OpenRouter chat/completions smoke through the explicit paid-call gate.",
    "command": "./repo-python tools/meta/control/openrouter_free_runtime.py smoke-chat --model {model} --allow-paid --max-tokens {max_tokens} --write",
    "parameters_schema": {
      "model": {
        "type": "string",
        "required": false,
        "default": "mistralai/mistral-nemo",
        "description": "OpenRouter model id for the paid-gated smoke."
      },
      "max_tokens": {
        "type": "integer",
        "required": false,
        "default": 16,
        "minimum": 1,
        "maximum": 128,
        "description": "Maximum output tokens for the smoke reply."
      }
    },
    "ui_group": "providers",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_086",
      "pri_104"
    ]
  },
  {
    "operation_id": "provider_transform_job",
    "label": "Provider transform job",
    "kicker": "providers",
    "description_short": "Run one lower-class Type A transform_job through the runtime-owned worker harness; writes provider_receipt and optional row_patch under state/compute_workers.",
    "command": "./repo-python tools/meta/control/type_a_worker_harness.py run --job-path \"{job_path}\" --provider-id {provider_id}",
    "parameters_schema": {
      "job_path": {
        "type": "string",
        "required": true,
        "label": "Transform job",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative transform_job JSON path."
      },
      "provider_id": {
        "type": "string",
        "required": false,
        "default": "auto",
        "label": "Provider",
        "pattern": "^[A-Za-z0-9_./-]+$",
        "description": "Provider id: auto, nvidia_nim, or openrouter_api."
      }
    },
    "ui_group": "providers",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_086",
      "pri_104",
      "pri_111"
    ],
    "meta_mission_id": "provider_transform_job",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "provider_transform_materialize",
    "label": "Materialize provider transform job",
    "kicker": "providers",
    "description_short": "Materialize one provider-model-catalog row job into a provider_transform_job draft without dispatching a provider.",
    "command": "./repo-python tools/meta/control/type_a_worker_harness.py materialize-row-job --source {source} --target-row-id \"{target_row_id}\" --limit {limit}",
    "parameters_schema": {
      "source": {
        "type": "string",
        "required": false,
        "default": "provider-model-catalog",
        "label": "Row-job source",
        "pattern": "^[A-Za-z0-9_.-]+$",
        "description": "Metabolism row-job source. Only provider-model-catalog rows can materialize."
      },
      "target_row_id": {
        "type": "string",
        "required": true,
        "label": "Target row id",
        "pattern": "^[A-Za-z0-9_./:; -]+$",
        "description": "target_row_id of the provider-model-catalog row job to materialize, e.g. provider_model:nvidia_nim:z-ai/glm-5.1."
      },
      "limit": {
        "type": "integer",
        "required": false,
        "default": 50,
        "minimum": 1,
        "maximum": 500,
        "description": "Row-job lookup window. Increase only if the target row falls outside the default catalog slice."
      }
    },
    "ui_group": "providers",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_086",
      "pri_104",
      "pri_111"
    ],
    "meta_mission_id": "provider_transform_materialize",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "work_ledger_project",
    "label": "Refresh work ledger",
    "kicker": "ledger",
    "description_short": "Deterministically rebuild all work-ledger projections from the append-only JSONL substrate.",
    "command": "./repo-python tools/meta/factory/work_ledger.py project --all",
    "parameters_schema": {},
    "principle_refs": [
      "pri_086",
      "pri_104"
    ]
  },
  {
    "operation_id": "paper_module_authoring_prepare",
    "label": "Prepare paper-module run",
    "kicker": "paper-modules",
    "description_short": "Validate one paper-module authoring packet and materialize a durable authoring bundle plus draft scaffold.",
    "command": "./repo-python tools/meta/factory/paper_module_authoring_runtime.py --packet \"{packet_path}\"",
    "parameters_schema": {
      "packet_path": {
        "type": "string",
        "required": true,
        "label": "Packet path",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute path to a paper_module_authoring packet JSON."
      }
    },
    "ui_group": "paper_modules",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_097",
      "pri_111"
    ],
    "meta_mission_id": "paper_module_authoring",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "kernel_doctrine_query",
    "label": "Doctrine query",
    "kicker": "doctrine",
    "description_short": "Compiled doctrine query packet for a topic across the authority graph.",
    "command": "python3 kernel.py --doctrine-query \"{topic}\"",
    "parameters_schema": {
      "topic": {
        "type": "string",
        "required": true,
        "description": "Doctrine topic (e.g. 'bridge dispatch')."
      }
    },
    "principle_refs": [
      "pri_086"
    ]
  },
  {
    "operation_id": "kernel_raw_seed_browse",
    "label": "Raw-seed browse",
    "kicker": "raw-seed",
    "description_short": "Browse raw-seed paragraphs in the active family for a query.",
    "command": "python3 kernel.py --raw-seed-browse {family} --query \"{query}\"",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "description": "Phase family id."
      },
      "query": {
        "type": "string",
        "required": true,
        "description": "Search term for raw-seed paragraphs."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "kernel_sync_raw_seed",
    "label": "Sync raw seed",
    "kicker": "raw-seed",
    "description_short": "Mechanically sync a family raw seed and regenerate its registry projections.",
    "command": "python3 kernel.py --sync-raw-seed {family} --live",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "description": "Phase family id, e.g. '09'."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_sync",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "kernel_sync_raw_seed_auto",
    "label": "Auto sync raw seed",
    "kicker": "raw-seed",
    "description_short": "Auto-settle raw-seed sync lane used by metabolismd after an intake session settles.",
    "command": "python3 kernel.py --sync-raw-seed {family} --live",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "description": "Phase family id, e.g. '09'."
      },
      "entry_id": {
        "type": "string",
        "required": false,
        "description": "Settled raw-seed intake entry id for tracker correlation."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_sync",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_atomize",
    "label": "Atomize raw seed (local)",
    "kicker": "raw-seed",
    "description_short": "Fast local backlog drain: atomize selected raw-seed bins directly into extracted-shard rows and refresh family coverage.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py atomize --family {family} --substrate {substrate} --cohort-size {cohort_size} --selection-mode {selection_mode}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Sibling substrate lane: raw_seed or agent_seed."
      },
      "cohort_size": {
        "type": "integer",
        "required": false,
        "default": 12,
        "minimum": 1,
        "label": "Cohort size",
        "description": "How many pending bins are selected into this bounded run."
      },
      "selection_mode": {
        "type": "string",
        "required": false,
        "default": "fresh_first",
        "label": "Selection mode",
        "description": "Bin selection order: fresh_first, oldest_first, or mixed."
      }
    },
    "dispatch_policy_mission_id": "raw_seed_atomization",
    "dispatch_policy_binding": {
      "cohort_param": "cohort_size"
    },
    "principle_refs": [
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_atomization",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_atomize_cycle",
    "label": "Plan raw-seed atomize cycle",
    "kicker": "raw-seed",
    "description_short": "Materialize a mission-backed atomization run root and import contract without dispatching bridge work yet.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py atomize-cycle --family {family} --substrate {substrate} --provider {provider} --cohort-size {cohort_size} --wave-width {wave_width} --selection-mode {selection_mode}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Sibling substrate lane: raw_seed or agent_seed."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key for the later atomization launch."
      },
      "cohort_size": {
        "type": "integer",
        "required": false,
        "default": 12,
        "minimum": 1,
        "label": "Cohort size",
        "description": "How many pending paragraphs are selected into this atomization cycle."
      },
      "wave_width": {
        "type": "integer",
        "required": false,
        "default": 3,
        "minimum": 1,
        "label": "Wave width",
        "description": "How many selected paragraphs should dispatch at once when the planned run is launched later."
      },
      "selection_mode": {
        "type": "string",
        "required": false,
        "default": "fresh_first",
        "label": "Selection mode",
        "description": "Bin selection order: fresh_first, oldest_first, or mixed."
      }
    },
    "dispatch_policy_mission_id": "raw_seed_atomization",
    "dispatch_policy_binding": {
      "provider_param": "provider",
      "cohort_param": "cohort_size",
      "wave_param": "wave_width"
    },
    "validation_policy": {
      "dispatch_policy_mission_id": "raw_seed_atomization",
      "provider_param": "provider",
      "wave_param": "wave_width"
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_atomization",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_distill_ingest",
    "label": "Ingest raw-seed distillation",
    "kicker": "raw-seed",
    "description_short": "Store bridge-authored paragraph distillations with paragraph provenance so later atomization can reuse them.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py distill-ingest --family {family} --input {input_path} --provider {provider}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "description": "Phase family id, e.g. '09'."
      },
      "input_path": {
        "type": "string",
        "required": true,
        "description": "Repo-relative or absolute JSON payload path for the distillation batch."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "description": "Bridge provider key used for provenance metadata."
      }
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "raw_seed_distill_cycle",
    "label": "Distill raw seed",
    "kicker": "raw-seed",
    "description_short": "Run one bounded bridge-first raw-seed distillation cycle over pending bins.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py distill-cycle --family {family} --substrate {substrate} --provider {provider} --cohort-size {cohort_size} --wave-width {wave_width} --selection-mode {selection_mode} --paragraphs-per-probe {paragraphs_per_probe}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Sibling substrate lane: raw_seed or agent_seed."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key used for distillation dispatch."
      },
      "cohort_size": {
        "type": "integer",
        "required": false,
        "default": 12,
        "minimum": 1,
        "label": "Cohort size",
        "description": "How many pending paragraphs are selected into this distillation cycle."
      },
      "wave_width": {
        "type": "integer",
        "required": false,
        "default": 3,
        "minimum": 1,
        "label": "Wave width",
        "description": "How many selected paragraphs dispatch at once. Must stay at or below the provider ceiling."
      },
      "selection_mode": {
        "type": "string",
        "required": false,
        "default": "oldest_first",
        "label": "Selection mode",
        "description": "Bin selection order: fresh_first, oldest_first, or mixed."
      },
      "paragraphs_per_probe": {
        "type": "integer",
        "required": false,
        "default": 1,
        "minimum": 1,
        "label": "Paragraphs per probe",
        "description": "How many focus paragraphs to pack into each bridge prompt. >1 batches multiple paragraphs into one conversation to reduce rate-limiter pressure. Total probes per cycle = ceil(cohort_size / paragraphs_per_probe)."
      }
    },
    "dispatch_policy_mission_id": "raw_seed_bridge_distillation",
    "dispatch_policy_binding": {
      "provider_param": "provider",
      "cohort_param": "cohort_size",
      "wave_param": "wave_width"
    },
    "validation_policy": {
      "dispatch_policy_mission_id": "raw_seed_bridge_distillation",
      "provider_param": "provider",
      "wave_param": "wave_width"
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_bridge_distillation",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_context_pack",
    "label": "Plan raw-seed contextual compression",
    "kicker": "raw-seed",
    "description_short": "Materialize candidate raw-seed contextual compression rows with profile ids, skill ids, drilldown refs, dynamic facts, and omission receipts. Does not dispatch bridge work or mutate doctrine.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py context-pack --family {family} --substrate {substrate} --cohort-size {cohort_size} --selection-mode {selection_mode} --paragraphs-per-probe {paragraphs_per_probe}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Sibling substrate lane: raw_seed or agent_seed."
      },
      "cohort_size": {
        "type": "integer",
        "required": false,
        "default": 12,
        "minimum": 1,
        "label": "Cohort size",
        "description": "How many pending paragraphs are selected into this contextual packet run."
      },
      "selection_mode": {
        "type": "string",
        "required": false,
        "default": "oldest_first",
        "label": "Selection mode",
        "description": "Bin selection order: fresh_first, oldest_first, or mixed."
      },
      "paragraphs_per_probe": {
        "type": "integer",
        "required": false,
        "default": 6,
        "minimum": 1,
        "label": "Paragraphs per packet",
        "description": "How many focus paragraphs to pack into each contextual candidate packet."
      }
    },
    "ui_group": "raw_seed",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_086",
      "pri_107",
      "pri_111"
    ],
    "meta_mission_id": "raw_seed_contextual_compression",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_route_review",
    "label": "Route raw-seed backlog",
    "kicker": "raw-seed",
    "description_short": "Write grouped doctrine-routing proposals for pending atomized bins with provider-safe batching.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py route-review --family {family} --substrate {substrate} --provider {provider} --cohort-size {cohort_size} --wave-width {wave_width} --selection-mode {selection_mode}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Sibling substrate lane: raw_seed or agent_seed."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key used for batching policy, e.g. 'chatgpt' or 'gemini'."
      },
      "cohort_size": {
        "type": "integer",
        "required": false,
        "default": 10,
        "minimum": 1,
        "label": "Cohort size",
        "description": "How many pending bins are selected into this review batch."
      },
      "wave_width": {
        "type": "integer",
        "required": false,
        "default": 3,
        "minimum": 1,
        "label": "Wave width",
        "description": "How many selected bins dispatch at once. Must stay at or below the provider ceiling."
      },
      "selection_mode": {
        "type": "string",
        "required": false,
        "default": "fresh_first",
        "label": "Selection mode",
        "description": "Bin selection order: fresh_first, oldest_first, or mixed."
      },
      "group": {
        "type": "string",
        "required": false,
        "label": "Group",
        "description": "Optional idea_group_id that narrows route-review to one pending routing bin family."
      }
    },
    "optional_cli_flags": {
      "group": "--shards-group {group}"
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ],
    "dispatch_policy_mission_id": "raw_seed_doctrine_routing",
    "dispatch_policy_binding": {
      "provider_param": "provider",
      "cohort_param": "cohort_size",
      "wave_param": "wave_width"
    },
    "validation_policy": {
      "dispatch_policy_mission_id": "raw_seed_doctrine_routing",
      "provider_param": "provider",
      "wave_param": "wave_width"
    },
    "meta_mission_id": "raw_seed_doctrine_routing",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_maintenance_campaign_launch",
    "label": "Launch maintenance campaign",
    "kicker": "maintenance",
    "description_short": "Mine raw-seed runtime findings, bin them, and launch preview-first bridge authoring packets for each maintenance bin.",
    "command": "./repo-python tools/meta/factory/raw_seed_maintenance_campaign.py --family {family} --provider {provider} --run-session --preview-apply --max-bins {max_bins}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key used for maintenance authoring."
      },
      "max_bins": {
        "type": "integer",
        "required": false,
        "default": 0,
        "minimum": 0,
        "label": "Max bins",
        "description": "Optional cap on how many mined bins to process; 0 means all bins."
      }
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_111"
    ],
    "meta_mission_id": "raw_seed_maintenance_population",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_maintenance_campaign_resume",
    "label": "Resume maintenance campaign",
    "kicker": "maintenance",
    "description_short": "Resume a prior raw-seed maintenance authoring campaign from its stored campaign summary.",
    "command": "./repo-python tools/meta/factory/raw_seed_maintenance_campaign.py --resume-campaign-summary {campaign_summary} --provider {provider} --run-session --preview-apply",
    "parameters_schema": {
      "campaign_summary": {
        "type": "string",
        "required": true,
        "label": "Campaign summary",
        "description": "Repo-relative or absolute path to an existing raw_seed_maintenance campaign_summary.json."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key used when rerunning incomplete maintenance batches."
      }
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_111"
    ],
    "meta_mission_id": "raw_seed_maintenance_population",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "python_std_compliance_campaign_launch",
    "label": "Launch Python compliance campaign",
    "kicker": "python-std",
    "description_short": "Mine persisted std_python backlog findings, bin them, and launch preview-first bridge authoring packets for each compliance bin.",
    "command": "./repo-python tools/meta/factory/python_std_compliance_campaign.py --provider {provider} --run-session --preview-apply --max-bins {max_bins}",
    "parameters_schema": {
      "provider": {
        "type": "string",
        "required": false,
        "default": "auto",
        "label": "Provider",
        "description": "Optional provider override for all bins. Use 'auto' to respect each bin's recommended provider."
      },
      "max_bins": {
        "type": "integer",
        "required": false,
        "default": 0,
        "minimum": 0,
        "label": "Max bins",
        "description": "Optional cap on how many mined bins to process; 0 means all bins."
      }
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_111"
    ],
    "meta_mission_id": "python_std_compliance_authoring",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "python_std_compliance_campaign_resume",
    "label": "Resume Python compliance campaign",
    "kicker": "python-std",
    "description_short": "Resume a prior std_python compliance authoring campaign from its stored campaign summary.",
    "command": "./repo-python tools/meta/factory/python_std_compliance_campaign.py --resume-campaign-summary {campaign_summary} --provider {provider} --run-session --preview-apply",
    "parameters_schema": {
      "campaign_summary": {
        "type": "string",
        "required": true,
        "label": "Campaign summary",
        "description": "Repo-relative or absolute path to an existing python_std_compliance campaign_summary.json."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "auto",
        "label": "Provider",
        "description": "Optional provider override when rerunning incomplete compliance batches. Use 'auto' to respect each bin's recommended provider."
      }
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_111"
    ],
    "meta_mission_id": "python_std_compliance_authoring",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "python_std_compliance_cycle",
    "label": "Advance Python compliance cycle",
    "kicker": "python-std",
    "description_short": "Advance the std_python compliance lane by one idempotent preview, approval-gate, or live-apply step.",
    "command": "./repo-python tools/meta/factory/python_std_compliance_cycle.py --provider {provider}",
    "parameters_schema": {
      "provider": {
        "type": "string",
        "required": false,
        "default": "auto",
        "label": "Provider",
        "description": "Optional provider override for preview launches or resumes. Use 'auto' to respect bin recommendations."
      }
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_111"
    ],
    "meta_mission_id": "python_std_compliance_authoring",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "python_std_compliance_campaign_approve",
    "label": "Approve Python compliance campaign",
    "kicker": "python-std",
    "description_short": "Record the one-time approval that promotes a preview-ready std_python compliance snapshot into the auto-drain apply lane.",
    "command": "./repo-python tools/meta/factory/python_std_compliance_cycle.py --approve-campaign-summary {campaign_summary} --approved-by {approved_by}",
    "parameters_schema": {
      "campaign_summary": {
        "type": "string",
        "required": true,
        "label": "Campaign summary",
        "description": "Repo-relative or absolute path to an existing preview-ready python_std compliance campaign_summary.json."
      },
      "approved_by": {
        "type": "string",
        "required": false,
        "default": "human_operator",
        "label": "Approved by",
        "description": "Operator identifier recorded in the approval metadata."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_111"
    ]
  },
  {
    "operation_id": "factory_stage_apply",
    "label": "Regenerate staged apply",
    "kicker": "factory",
    "description_short": "Regenerate the factory staged apply packet through the canonical stage-apply step.",
    "command": "./repo-python tools/meta/factory/factory_runner.py --step stage_apply",
    "parameters_schema": {},
    "ui_group": "factory",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_058",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "raw_seed_provider_candidate_cycle",
    "label": "Raw-seed provider candidates",
    "kicker": "raw-seed",
    "description_short": "Materialize fresh-first raw-seed Type B candidate jobs and enqueue NVIDIA/OpenRouter provider_transform_job work. No bridge dispatch and no source mutation.",
    "command": "./repo-python tools/meta/control/type_a_worker_harness.py materialize-row-jobs --source raw-seed-provider-candidates --limit {limit} --family {family} --substrate {substrate} --selection-mode {selection_mode} --providers {providers} --write --enqueue",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Raw seed substrate lane."
      },
      "selection_mode": {
        "type": "string",
        "required": false,
        "default": "fresh_first",
        "label": "Selection mode",
        "description": "Paragraph selection order: fresh_first, oldest_first, or mixed."
      },
      "providers": {
        "type": "string",
        "required": false,
        "default": "nvidia_nim,openrouter_api",
        "pattern": "^[A-Za-z0-9_,./-]+$",
        "label": "Providers",
        "description": "Comma-separated Type B provider ids."
      },
      "limit": {
        "type": "integer",
        "required": false,
        "default": 8,
        "minimum": 1,
        "maximum": 40,
        "label": "Limit",
        "description": "How many provider row jobs to materialize and enqueue."
      }
    },
    "ui_group": "raw_seed",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_086",
      "pri_107",
      "pri_111"
    ],
    "meta_mission_id": "raw_seed_type_b_provider_candidates",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "raw_seed_sync_handoff_launch",
    "label": "Fresh sync handoff",
    "kicker": "raw-seed",
    "description_short": "Run the fresh-first post-sync handoff chain: distill, atomize, route-review, coverage-refresh, and surface.",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --chain raw_seed_sync_handoff --family {family} --provider {provider}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key used by the distillation step."
      }
    },
    "ui_group": "raw_seed",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_sync_handoff",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "raw_seed_prepare_subagent_packet",
    "label": "Prepare subagent distillation packet",
    "kicker": "raw-seed",
    "description_short": "Pick N untouched paragraphs, mark them in_flight in the ledger, and write a dispatch packet for the Type A subagent lane. Does NOT spawn subagents; the conductor consumes the packet.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py backlog-slice --family {family} --substrate {substrate} --cohort-size {cohort_size} --wave-width {wave_width} --strategy {strategy}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Sibling substrate lane: raw_seed or agent_seed."
      },
      "cohort_size": {
        "type": "integer",
        "required": false,
        "default": 6,
        "minimum": 1,
        "label": "Cohort size",
        "description": "Paragraphs per cohort."
      },
      "wave_width": {
        "type": "integer",
        "required": false,
        "default": 2,
        "minimum": 1,
        "label": "Wave width",
        "description": "Recorded wave_width controlling later conductor parallelism."
      },
      "strategy": {
        "type": "string",
        "required": false,
        "default": "simple_first",
        "label": "Strategy",
        "description": "Paragraph ordering: simple_first, complex_last, or random."
      }
    },
    "ui_group": "raw_seed",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "raw_seed_subagent_drop_ingest",
    "label": "Ingest subagent distillation drop",
    "kicker": "raw-seed",
    "description_short": "Validate and import subagent-returned distillation bundles, recording ledger transitions. Runs after a conductor drops bundles.json alongside the dispatched packet.",
    "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py subagent-import --packet-path {packet_path} --bundles-path {bundles_path} --substrate {substrate}",
    "parameters_schema": {
      "packet_path": {
        "type": "string",
        "required": true,
        "label": "Packet path",
        "description": "Repo-relative path to the packet.json written by backlog-slice."
      },
      "bundles_path": {
        "type": "string",
        "required": true,
        "label": "Bundles path",
        "description": "Repo-relative path to the JSON file holding conductor-collected subagent bundles."
      },
      "substrate": {
        "type": "string",
        "required": false,
        "default": "raw_seed",
        "label": "Substrate",
        "description": "Sibling substrate lane: raw_seed or agent_seed."
      },
      "strict": {
        "type": "boolean",
        "required": false,
        "default": false,
        "label": "Strict",
        "description": "Drop any paragraph containing a validator-rejected shard; advisory otherwise."
      }
    },
    "ui_group": "raw_seed",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "raw_seed_apply_routing",
    "label": "Apply routed doctrine",
    "kicker": "raw-seed",
    "description_short": "Commit bounded routing-review proposals into doctrine and refresh the enriched coverage view.",
    "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py apply-routing --family {family} --commit",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "description": "Phase family id, e.g. '09'."
      }
    },
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "raw_seed_coverage_enrich",
    "label": "Refresh coverage health",
    "kicker": "raw-seed",
    "description_short": "Rebuild the enriched raw-seed coverage surface with density, merge, and orphan-cluster signals.",
    "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py coverage-enrich --family {family}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "description": "Phase family id, e.g. '09'."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_coverage_enrich",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "raw_seed_surface_to_codex",
    "label": "Surface to Codex",
    "kicker": "raw-seed",
    "description_short": "Promote low-confidence routes and proposed-new items into the Codex review queue without mutating doctrine.",
    "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py surface-to-codex --family {family}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "description": "Phase family id, e.g. '09'."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_surface_to_codex",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "evolve_input_check",
    "label": "Check Evolve inputs",
    "kicker": "evolve",
    "description_short": "Validate a Lab subject run and Oracle truth run before Evolve can learn from the pair.",
    "command": "./repo-python tools/refinement/run_evolve.py --subject-run \"{subject_run}\" --truth-run \"{truth_run}\" --input-check",
    "parameters_schema": {
      "subject_run": {
        "type": "string",
        "required": true,
        "label": "Subject run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Lab run directory at T-n."
      },
      "truth_run": {
        "type": "string",
        "required": true,
        "label": "Truth run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Oracle truth run directory at T."
      }
    },
    "ui_group": "lab_oracle_evolve",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_097",
      "pri_111"
    ],
    "meta_mission_id": "lab_oracle_evolve_input_check",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "evolve_bridge_dry_run",
    "label": "Run Evolve dry-run",
    "kicker": "evolve",
    "description_short": "Run the bridge-backed Evolve analysis for a ready Lab/Oracle pair, previewing dossier patches without applying them.",
    "command": "./repo-python tools/refinement/run_evolve.py --subject-run \"{subject_run}\" --truth-run \"{truth_run}\" --bridge --provider {provider} --dry-run",
    "parameters_schema": {
      "subject_run": {
        "type": "string",
        "required": true,
        "label": "Subject run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Lab run directory at T-n."
      },
      "truth_run": {
        "type": "string",
        "required": true,
        "label": "Truth run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Oracle truth run directory at T."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider used for delta analysis and optional dossier patch synthesis."
      }
    },
    "ui_group": "lab_oracle_evolve",
    "execution_mode": "detached",
    "principle_refs": [
      "pri_049",
      "pri_097",
      "pri_111"
    ],
    "meta_mission_id": "lab_oracle_evolve_bridge_dry_run",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "lab_oracle_evolve_overnight_plan",
    "label": "Plan overnight Evolve ledger",
    "kicker": "evolve",
    "description_short": "Resolve a bridge-budgeted overnight Evolve queue and append the plan to the run-pair training ledger without executing bridge jobs.",
    "command": "./repo-python tools/refinement/overnight_ledger.py --budget-units {budget_units} --provider {provider} --max-runs {max_runs} --write-ledger",
    "parameters_schema": {
      "budget_units": {
        "type": "string",
        "required": false,
        "default": "3",
        "label": "Budget units",
        "pattern": "^[0-9]+(?:\\.[0-9]+)?$",
        "description": "Abstract bridge budget units. One ready pair starts at 1.0 unit plus target-size overhead."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider to encode in planned Evolve dry-run commands."
      },
      "max_runs": {
        "type": "integer",
        "required": false,
        "default": 6,
        "minimum": 1,
        "label": "Max runs",
        "description": "Hard cap on selected run pairs for this overnight plan."
      }
    },
    "ui_group": "lab_oracle_evolve",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_097",
      "pri_111"
    ],
    "meta_mission_id": "lab_oracle_evolve_overnight_ledger",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "oracle_quartet_plan",
    "label": "Plan Oracle quartet repair",
    "kicker": "oracle",
    "description_short": "Inspect the canonical Oracle quartet for an Evolve run pair and return alias or rerun repair actions.",
    "command": "./repo-python tools/oracle/run_quartet.py --subject-run \"{subject_run}\" --truth-run \"{truth_run}\" --plan",
    "parameters_schema": {
      "subject_run": {
        "type": "string",
        "required": true,
        "label": "Subject run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Lab run directory at T-n."
      },
      "truth_run": {
        "type": "string",
        "required": true,
        "label": "Truth run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Oracle truth run directory at T."
      }
    },
    "ui_group": "lab_oracle_evolve",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_049",
      "pri_097",
      "pri_111"
    ],
    "meta_mission_id": "oracle_quartet_repair",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "oracle_quartet_run_missing",
    "label": "Run Oracle quartet repair",
    "kicker": "oracle",
    "description_short": "Resume the Oracle engine at a selected quartet source node so modern runs dual-write the canonical artifact aliases.",
    "command": "./repo-python tools/oracle/run_quartet.py --subject-run \"{subject_run}\" --truth-run \"{truth_run}\" --run-missing --target {target}",
    "parameters_schema": {
      "subject_run": {
        "type": "string",
        "required": true,
        "label": "Subject run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Lab run directory at T-n."
      },
      "truth_run": {
        "type": "string",
        "required": true,
        "label": "Truth run",
        "pattern": "^[A-Za-z0-9_./ -]+$",
        "description": "Repo-relative or absolute Oracle truth run directory at T."
      },
      "target": {
        "type": "string",
        "required": false,
        "default": "oracle_cp2_emitter",
        "label": "Target",
        "pattern": "^[A-Za-z0-9_./-]+$",
        "description": "Quartet source node to resume: oracle_truth_diff_equity, oracle_truth_map, oracle_attribution_map, or oracle_cp2_emitter."
      }
    },
    "ui_group": "lab_oracle_evolve",
    "execution_mode": "detached",
    "principle_refs": [
      "pri_049",
      "pri_097",
      "pri_111"
    ],
    "meta_mission_id": "oracle_quartet_repair",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "overnight_raw_seed_chain_launch",
    "label": "Launch overnight chain",
    "kicker": "overnight",
    "description_short": "Start the detached raw-seed overnight chain (conservative cohort/wave caps) with ledger under state/meta_missions/overnight_raw_seed_chain/runtime/ and graceful-stop via overnight_stop.flag.",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --chain overnight_raw_seed_chain --family {family} --provider {provider} --cohort-override distill=4 --wave-override distill=1 --cohort-override atomize=8 --wave-override atomize=2 --cohort-override route_review=8 --wave-override route_review=2",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key used by the chain's bridge-backed steps."
      }
    },
    "ui_group": "overnight_chain",
    "execution_mode": "detached",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "overnight_raw_seed_chain",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "overnight_raw_seed_chain_resume",
    "label": "Resume overnight chain",
    "kicker": "overnight",
    "description_short": "Resume the most recent graceful-stop or failed overnight chain from its next durable seam (same conservative cohort/wave flags as launch).",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --chain overnight_raw_seed_chain --family {family} --provider {provider} --cohort-override distill=4 --wave-override distill=1 --cohort-override atomize=8 --wave-override atomize=2 --cohort-override route_review=8 --wave-override route_review=2 --resume",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key used by the chain's bridge-backed steps."
      }
    },
    "ui_group": "overnight_chain",
    "execution_mode": "detached",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "overnight_raw_seed_chain",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "overnight_raw_seed_chain_stop",
    "label": "Stop overnight chain",
    "kicker": "overnight",
    "description_short": "Set overnight_stop.flag for a graceful stop at the next chain seam; also stops drain-distill-raw-seed (same flag).",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py stop --chain overnight_raw_seed_chain --family {family}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      }
    },
    "ui_group": "overnight_chain",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "overnight_raw_seed_drain_distill_launch",
    "label": "Drain raw-seed distill (overnight)",
    "kicker": "overnight",
    "description_short": "Loop bridge distill-cycles with conservative defaults until the backlog is empty, max-passes, or stop (ledger: drain_distill_ledger.jsonl; stop: overnight_raw_seed_chain/runtime/overnight_stop.flag).",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py drain-distill-raw-seed --family {family} --provider {provider} --max-passes {max_passes} --sleep-seconds {sleep_seconds} --cohort-size {cohort_size} --wave-width {wave_width}",
    "parameters_schema": {
      "family": {
        "type": "string",
        "required": false,
        "default": "09",
        "label": "Family",
        "description": "Phase family id, e.g. '09'."
      },
      "provider": {
        "type": "string",
        "required": false,
        "default": "chatgpt",
        "label": "Provider",
        "description": "Bridge provider key for distill-cycle."
      },
      "max_passes": {
        "type": "integer",
        "required": false,
        "default": 2000,
        "minimum": 1,
        "label": "Max passes",
        "description": "Upper bound on distill-cycle invocations."
      },
      "sleep_seconds": {
        "type": "integer",
        "required": false,
        "default": 45,
        "minimum": 0,
        "label": "Sleep seconds",
        "description": "Pause between successful passes to limit bridge throughput."
      },
      "cohort_size": {
        "type": "integer",
        "required": false,
        "default": 4,
        "minimum": 1,
        "label": "Cohort size",
        "description": "Paragraphs per distill-cycle (conservative default 4)."
      },
      "wave_width": {
        "type": "integer",
        "required": false,
        "default": 1,
        "minimum": 1,
        "label": "Wave width",
        "description": "Concurrent bridge dispatches (conservative default 1)."
      }
    },
    "ui_group": "overnight_chain",
    "execution_mode": "detached",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "raw_seed_bridge_distillation",
    "meta_mission_run_source": "runtime"
  },
  {
    "operation_id": "overnight_meta_mission_queue_launch",
    "label": "Launch autonomy runtime",
    "kicker": "overnight",
    "description_short": "Run a manifest-backed serial autonomy runtime of Type A seed observations, chains, and sync launchable operations.",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --manifest {manifest}",
    "parameters_schema": {
      "manifest": {
        "type": "string",
        "required": true,
        "label": "Manifest",
        "description": "Repo-relative or absolute path to an autonomy_runtime manifest JSON file; legacy meta_mission_queue manifests are accepted."
      },
      "family": {
        "type": "string",
        "required": false,
        "label": "Family",
        "description": "Optional family override injected into queue items that do not already set family."
      },
      "provider": {
        "type": "string",
        "required": false,
        "label": "Provider",
        "description": "Optional provider override injected into queue items that do not already set provider."
      }
    },
    "optional_cli_flags": {
      "family": "--family {family}",
      "provider": "--provider {provider}"
    },
    "ui_group": "overnight_queue",
    "execution_mode": "detached",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107",
      "pri_111"
    ]
  },
  {
    "operation_id": "overnight_meta_mission_queue_resume",
    "label": "Resume autonomy runtime",
    "kicker": "overnight",
    "description_short": "Resume a manifest-backed autonomy runtime from its next durable item seam.",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --manifest {manifest} --resume",
    "parameters_schema": {
      "manifest": {
        "type": "string",
        "required": true,
        "label": "Manifest",
        "description": "Repo-relative or absolute path to an autonomy_runtime manifest JSON file; legacy meta_mission_queue manifests are accepted."
      },
      "family": {
        "type": "string",
        "required": false,
        "label": "Family",
        "description": "Optional family override injected into queue items that do not already set family."
      },
      "provider": {
        "type": "string",
        "required": false,
        "label": "Provider",
        "description": "Optional provider override injected into queue items that do not already set provider."
      }
    },
    "optional_cli_flags": {
      "family": "--family {family}",
      "provider": "--provider {provider}"
    },
    "ui_group": "overnight_queue",
    "execution_mode": "detached",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107",
      "pri_111"
    ]
  },
  {
    "operation_id": "overnight_meta_mission_queue_stop",
    "label": "Stop autonomy runtime",
    "kicker": "overnight",
    "description_short": "Request a graceful stop for a manifest-backed autonomy runtime at the next item seam.",
    "command": "./repo-python tools/meta/factory/overnight_chain_runner.py stop --manifest {manifest}",
    "parameters_schema": {
      "manifest": {
        "type": "string",
        "required": true,
        "label": "Manifest",
        "description": "Repo-relative or absolute path to an autonomy_runtime manifest JSON file; legacy meta_mission_queue manifests are accepted."
      }
    },
    "ui_group": "overnight_queue",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_072",
      "pri_086",
      "pri_107",
      "pri_111"
    ]
  },
  {
    "operation_id": "doctrine_edge_validate",
    "label": "Validate doctrine edges",
    "kicker": "doctrine",
    "description_short": "Report doctrine edges still missing forward_gloss or reverse_gloss without mutating the corpus.",
    "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py edge-validate",
    "parameters_schema": {},
    "principle_refs": [
      "pri_072",
      "pri_086"
    ]
  },
  {
    "operation_id": "doctrine_edge_migrate",
    "label": "Normalize doctrine edges",
    "kicker": "doctrine",
    "description_short": "Commit the bounded doctrine-edge migration and reciprocal back-mirror additions.",
    "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py edge-migrate --commit --apply-back-mirror",
    "parameters_schema": {},
    "principle_refs": [
      "pri_072",
      "pri_086"
    ]
  },
  {
    "operation_id": "paper_module_rediscovery_scan",
    "label": "Paper-module rediscovery scan",
    "kicker": "paper-modules",
    "description_short": "Mine operational-record rediscovery evidence into the paper-module coverage feedback artifact.",
    "command": "./repo-python tools/meta/factory/rediscovery_miner.py",
    "parameters_schema": {
      "mining_run_path": {
        "type": "string",
        "required": false,
        "label": "Mining run",
        "description": "Optional existing mining_run.json to consume instead of running the miner again."
      },
      "out_path": {
        "type": "string",
        "required": false,
        "label": "Output path",
        "description": "Optional output path for the generated rediscovery findings artifact."
      }
    },
    "optional_cli_flags": {
      "mining_run_path": "--mining-run {mining_run_path}",
      "out_path": "--out {out_path}"
    },
    "principle_refs": [
      "pri_086",
      "pri_107",
      "pri_111"
    ]
  },
  {
    "operation_id": "paper_module_coverage_refresh",
    "label": "Paper-module coverage refresh",
    "kicker": "paper-modules",
    "description_short": "Rebuild the paper-module index and validation report after a high-signal rediscovery scan.",
    "command": "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
    "parameters_schema": {},
    "principle_refs": [
      "pri_086",
      "pri_111"
    ]
  },
  {
    "operation_id": "kernel_phase",
    "label": "Kernel phase",
    "kicker": "phase",
    "description_short": "Phase focus packet for a given phase id.",
    "command": "python3 kernel.py --phase {phase_id}",
    "parameters_schema": {
      "phase_id": {
        "type": "string",
        "required": true,
        "description": "Phase id, e.g. '09.17'."
      }
    },
    "principle_refs": [
      "pri_059"
    ]
  },
  {
    "operation_id": "bridge_preflight",
    "label": "Bridge preflight",
    "kicker": "bridge",
    "description_short": "Run the bridge preflight script to validate adapter/route readiness.",
    "command": "./repo-python run_bridge_preflight.py",
    "parameters_schema": {},
    "principle_refs": [
      "pri_072"
    ]
  },
  {
    "operation_id": "transcript_archaeology_scan",
    "label": "Transcript archaeology scan",
    "kicker": "archaeology",
    "description_short": "Scan local .claude + .codex + bridge transport surfaces and emit a capability fingerprint.",
    "command": "./repo-python -m system.lib.transcript_archaeology scan --scope {scope}",
    "parameters_schema": {
      "scope": {
        "type": "string",
        "required": false,
        "default": "local",
        "label": "Scope",
        "description": "'local' scans only repo-local surfaces. 'full' also samples ~/.claude/projects and ~/.codex/sessions (counts only, never content)."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_107"
    ],
    "meta_mission_id": "transcript_archaeology",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "voice_archaeology_import_shards",
    "label": "Voice archaeology import",
    "kicker": "archaeology",
    "description_short": "Validate and import an archaeological shard bundle into the live archaeology substrate.",
    "command": "./repo-python tools/meta/factory/voice_archaeology_pipeline.py import-shards {bundle} --live",
    "parameters_schema": {
      "bundle": {
        "type": "string",
        "required": true,
        "description": "Repo-relative or absolute path to a voice-archaeology pending bundle JSON."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_111"
    ]
  },
  {
    "operation_id": "session_heartbeat_snapshot",
    "label": "Session heartbeat snapshot",
    "kicker": "heartbeat",
    "description_short": "Snapshot live Claude Code and Codex session heartbeats from the bridge transport artifacts.",
    "command": "./repo-python -m system.lib.session_heartbeat snapshot",
    "parameters_schema": {},
    "principle_refs": [
      "pri_086"
    ],
    "meta_mission_id": "session_heartbeat_watch",
    "meta_mission_run_source": "launcher"
  },
  {
    "operation_id": "market_snapshot",
    "label": "Market snapshot",
    "kicker": "market",
    "description_short": "Capture a point-in-time snapshot of index/ETF/volatility prices via yfinance and append to state/metabolism/market_timeline.jsonl. Driven by the metabolismd market clock at each named fire point.",
    "command": "./repo-python tools/meta/control/market_snapshot.py --fire-point {fire_point} --market-date {market_date} --market-timezone {market_timezone} --target-time-market {target_time_market} --target-time-utc {target_time_utc}",
    "parameters_schema": {
      "fire_point": {
        "type": "string",
        "required": true,
        "label": "Fire point",
        "description": "Named fire point from the market clock (e.g. open, close)."
      },
      "market_date": {
        "type": "string",
        "required": true,
        "label": "Market date",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
        "description": "Market date in ISO form (YYYY-MM-DD) for the configured timezone."
      },
      "market_timezone": {
        "type": "string",
        "required": true,
        "default": "America/New_York",
        "label": "Market timezone",
        "description": "IANA timezone used for the market schedule."
      },
      "snapshot_key": {
        "type": "string",
        "required": false,
        "label": "Snapshot key",
        "pattern": "^[A-Za-z0-9_./:-]+$",
        "description": "Durable market snapshot id emitted by the market clock."
      },
      "weekday": {
        "type": "string",
        "required": false,
        "label": "Weekday",
        "pattern": "^[a-z]+$",
        "description": "Lowercase weekday emitted by the market clock."
      },
      "is_weekend": {
        "type": "string",
        "required": false,
        "label": "Weekend flag",
        "pattern": "^(True|False|true|false|0|1)$",
        "description": "Boolean weekend flag emitted by the market clock."
      },
      "target_time_market": {
        "type": "string",
        "required": true,
        "label": "Target market time",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$",
        "description": "Scheduled fire timestamp in market time."
      },
      "target_time_utc": {
        "type": "string",
        "required": true,
        "label": "Target UTC time",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$",
        "description": "Scheduled fire timestamp in UTC."
      },
      "target_time_operator_local": {
        "type": "string",
        "required": false,
        "label": "Target operator-local time",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$",
        "description": "Scheduled fire timestamp in the operator's local timezone."
      },
      "operator_timezone": {
        "type": "string",
        "required": false,
        "label": "Operator timezone",
        "pattern": "^[A-Za-z0-9_+./-]+$",
        "description": "Operator timezone label emitted by the market clock."
      }
    },
    "principle_refs": [
      "pri_086"
    ]
  },
  {
    "operation_id": "market_feed_bundle",
    "label": "Market feed bundle",
    "kicker": "market",
    "ui_group": "market_feeds",
    "execution_mode": "detached",
    "description_short": "Run and publish the seven deterministic market-intelligence feed lanes for one named market-clock fire point, using the scheduled fire timestamp as runtime.time_anchor while the engine resolves the forecast horizon after that anchor.",
    "command": "./repo-python tools/finance/scheduled_feed_bundle.py --run-id {run_id} --time-anchor {target_time_utc} --fire-point {fire_point} --market-date {market_date} --target-time-market {target_time_market} --target-time-utc {target_time_utc}",
    "parameters_schema": {
      "run_id": {
        "type": "string",
        "required": true,
        "label": "Run id",
        "pattern": "^[A-Za-z0-9_.-]+$",
        "description": "Durable feed run id, e.g. FEEDS_20260424_open."
      },
      "bundle_key": {
        "type": "string",
        "required": false,
        "label": "Bundle key",
        "pattern": "^[A-Za-z0-9_./:-]+$",
        "description": "Stable idempotency key for this market feed bundle."
      },
      "fire_point": {
        "type": "string",
        "required": true,
        "label": "Fire point",
        "description": "Named fire point from the market clock."
      },
      "market_date": {
        "type": "string",
        "required": true,
        "label": "Market date",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
        "description": "Market date in ISO form (YYYY-MM-DD)."
      },
      "market_timezone": {
        "type": "string",
        "required": false,
        "default": "America/New_York",
        "label": "Market timezone",
        "description": "IANA timezone used for the market schedule."
      },
      "target_time_market": {
        "type": "string",
        "required": true,
        "label": "Target market time",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$",
        "description": "Scheduled fire timestamp in market time."
      },
      "target_time_utc": {
        "type": "string",
        "required": true,
        "label": "Target UTC time",
        "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})$",
        "description": "Scheduled fire timestamp in UTC."
      }
    },
    "principle_refs": [
      "pri_086",
      "pri_097"
    ]
  },
  {
    "operation_id": "station_design_reference_prompt",
    "label": "Design reference prompt",
    "kicker": "frontend",
    "ui_group": "frontend",
    "description_short": "Write a GPT Images frontend reference prompt pack from a Station view and brief. Prompt-pack only; does not generate images.",
    "command": "./repo-python -m tools.meta.observability.station_render reference-prompt --view {view} --sections {sections} --profile {profile} --brief \"{brief}\"",
    "parameters_schema": {
      "view": {
        "type": "string",
        "required": false,
        "default": "home",
        "label": "View",
        "description": "Station view slug from station_views.json.",
        "pattern": "^[A-Za-z0-9_-]+$"
      },
      "sections": {
        "type": "integer",
        "required": false,
        "default": 4,
        "minimum": 1,
        "maximum": 16,
        "label": "Sections",
        "description": "How many website/app sections the image reference should cover."
      },
      "profile": {
        "type": "string",
        "required": false,
        "default": "station",
        "label": "Profile",
        "description": "Prompt posture: station, landing, app, or editorial.",
        "pattern": "^(station|landing|app|editorial)$"
      },
      "brief": {
        "type": "string",
        "required": false,
        "default": "premium operator cockpit reference",
        "label": "Brief",
        "description": "Short design brief. Safe punctuation only; no shell metacharacters.",
        "pattern": "^[A-Za-z0-9_./ ,:-]+$"
      }
    },
    "principle_refs": [
      "pri_058",
      "pri_068",
      "pri_104",
      "pri_114"
    ]
  },
  {
    "operation_id": "annex_sync_digest",
    "label": "Annex sync digest",
    "kicker": "annex",
    "ui_group": "annex",
    "description_short": "Roll every repo-kind annex into one attention-first digest (review-only; no git pull).",
    "command": "./repo-python annex_import.py digest --stale-days {stale_days}",
    "parameters_schema": {
      "stale_days": {
        "type": "integer",
        "required": false,
        "default": 14,
        "minimum": 1,
        "label": "Stale threshold (days)",
        "description": "Flag annexes whose last_refreshed_at is older than this."
      }
    },
    "principle_refs": [
      "pri_068",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "annex_sync_digest_pull",
    "label": "Annex sync digest (pull)",
    "kicker": "annex",
    "ui_group": "annex",
    "description_short": "Metabolism-safe annex refresh: pull a bounded rotating chunk of repo-kind annexes, refresh their indexes, then roll into one digest.",
    "command": "./repo-python annex_import.py digest --run --quiet --stale-days {stale_days} --limit {limit}",
    "parameters_schema": {
      "stale_days": {
        "type": "integer",
        "required": false,
        "default": 14,
        "minimum": 1,
        "label": "Stale threshold (days)",
        "description": "Flag annexes whose last_refreshed_at is older than this."
      },
      "limit": {
        "type": "integer",
        "required": false,
        "default": 8,
        "minimum": 1,
        "maximum": 64,
        "label": "Annex chunk size",
        "description": "How many repo annexes one metabolism refresh may pull/index."
      }
    },
    "principle_refs": [
      "pri_068",
      "pri_086",
      "pri_107"
    ]
  },
  {
    "operation_id": "standard_skill_pairing_campaign",
    "label": "Standard-skill pairing campaign (candidate packet only)",
    "kicker": "compliance",
    "description_short": "Materialize a candidate-only standard_skill_pairing campaign packet from the hologram-projected pairing map. Wave_004A; never authors skills, never edits the registry, never mutates source.",
    "command": "./repo-python tools/meta/factory/build_standard_skill_pairing_campaign.py --write --report --max-targets {max_targets}",
    "parameters_schema": {
      "max_targets": {
        "type": "integer",
        "required": false,
        "default": 12,
        "minimum": 1,
        "maximum": 64,
        "label": "Max candidate targets",
        "description": "Bounded slice of missing standards to include in the campaign packet."
      }
    },
    "ui_group": "compliance",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_133",
      "pri_086",
      "pri_111"
    ]
  },
  {
    "operation_id": "compliance_autocure_campaign",
    "label": "Compliance autocure campaign (candidate packet only)",
    "kicker": "compliance",
    "description_short": "Materialize a candidate-only compliance_autocure campaign packet from the hologram-projected compliance ledger. Wave_004A; controller-gated promotion; no source mutation, no provider dispatch.",
    "command": "./repo-python tools/meta/factory/build_compliance_autocure_campaign.py --write --report --max-targets {max_targets}",
    "parameters_schema": {
      "max_targets": {
        "type": "integer",
        "required": false,
        "default": 12,
        "minimum": 1,
        "maximum": 64,
        "label": "Max candidate targets",
        "description": "Bounded slice of ready_now + below_floor entries to include in the campaign packet."
      }
    },
    "ui_group": "compliance",
    "execution_mode": "sync",
    "principle_refs": [
      "pri_133",
      "pri_086",
      "pri_111"
    ]
  }
]
"""


@dataclass(frozen=True)
class PreparedLaunch:
    operation: Dict[str, Any]
    command: str
    execution_mode: str
    resolved_parameters: Dict[str, str]


AUTONOMY_RUNTIME_OPERATION_ALIASES = {
    "overnight_meta_mission_queue_launch": "autonomy_runtime_launch",
    "overnight_meta_mission_queue_resume": "autonomy_runtime_resume",
    "overnight_meta_mission_queue_stop": "autonomy_runtime_stop",
}


def _canonicalize_autonomy_runtime_operations(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for operation in catalog:
        operation_id = str(operation.get("operation_id") or "").strip()
        canonical_id = AUTONOMY_RUNTIME_OPERATION_ALIASES.get(operation_id)
        if not canonical_id:
            normalized.append(operation)
            continue
        canonical = dict(operation)
        canonical["operation_id"] = canonical_id
        canonical["legacy_operation_ids"] = [operation_id]
        canonical["ui_group"] = "autonomy_runtime"
        canonical["kicker"] = "autonomy"
        normalized.append(canonical)
        alias = dict(canonical)
        alias["operation_id"] = operation_id
        alias["canonical_operation_id"] = canonical_id
        alias["legacy_alias"] = True
        normalized.append(alias)
    return normalized


CATALOG: list[dict[str, Any]] = _canonicalize_autonomy_runtime_operations(json.loads(_BASE_CATALOG_JSON))
CATALOG.append(
    {
        "operation_id": "kernel_build_stale_phases",
        "label": "Build stale phases",
        "kicker": "build",
        "description_short": "Rebuild only the stale hologram slices returned by the build-status helper.",
        "command": "python3 kernel.py --build --build-phases {phase_list}",
        "parameters_schema": {
            "phase_list": {
                "type": "string",
                "required": True,
                "label": "Phase list",
                "description": "Comma-separated stale hologram phase ids, e.g. DERIVED,UI,RAW,SELF.",
                "pattern": "^[A-Z0-9_,-]+$",
            }
        },
        "principle_refs": ["pri_058", "pri_086"],
    }
)


def get_launchable_operations_catalog() -> list[dict[str, Any]]:
    return [dict(operation) for operation in CATALOG]


def find_launchable_operation(operation_id: str) -> Optional[Dict[str, Any]]:
    token = str(operation_id or "").strip()
    for operation in CATALOG:
        if str(operation.get("operation_id") or "").strip() == token:
            return dict(operation)
    return None


def _operation_dispatch_policy_payload(repo_root: Path, op: Mapping[str, Any]) -> dict[str, Any]:
    mission_id = str(op.get("dispatch_policy_mission_id") or "").strip()
    if not mission_id:
        return {}
    try:
        template = load_mission_template(repo_root, mission_id)
    except ValueError:
        try:
            template = load_mission_template(REPO_ROOT, mission_id)
        except ValueError:
            return {}
    authored_dispatch_policy = (
        template.get("dispatch_policy")
        if isinstance(template.get("dispatch_policy"), Mapping)
        else {}
    )
    summary = summarize_dispatch_policy(
        mission_dispatch_policy={
            **dict(authored_dispatch_policy or {}),
            "mission_id": mission_id,
        },
        provider_capabilities_path=repo_root / "tools/meta/bridge/provider_capabilities.json",
    )
    binding = dict(op.get("dispatch_policy_binding") or {})
    schema = op.get("parameters_schema") if isinstance(op.get("parameters_schema"), Mapping) else {}
    provider_param = str(binding.get("provider_param") or "").strip() or None
    default_provider = None
    if provider_param and isinstance(schema.get(provider_param), Mapping):
        default_provider = str(schema[provider_param].get("default") or "").strip() or None
    provider_ceilings = (
        summary.get("provider_ceilings")
        if isinstance(summary.get("provider_ceilings"), Mapping)
        else {}
    )
    provider_ceiling = None
    if default_provider and provider_ceilings.get(default_provider) is not None:
        provider_ceiling = int(provider_ceilings.get(default_provider) or 0)
    return {
        **summary,
        **binding,
        "default_provider": default_provider,
        "provider_ceiling": provider_ceiling,
    }


def _operation_meta_mission_payload(repo_root: Path, op: Mapping[str, Any]) -> dict[str, Any]:
    mission_id = str(op.get("meta_mission_id") or "").strip()
    if not mission_id:
        return {}
    try:
        entry = _mmw.resolve_mission_entry(repo_root, mission_id)
    except Exception:
        entry = None
    if entry is None:
        return {"mission_id": mission_id}
    try:
        metrics = _mmw.aggregate_metrics(repo_root, mission_id)
    except Exception:
        metrics = {}
    return {
        "mission_id": mission_id,
        "title": str(entry.get("title") or mission_id),
        "kind": str(entry.get("kind") or ""),
        "status": str(entry.get("status") or ""),
        "workspace_root": str(entry.get("workspace_root") or f"state/meta_missions/{mission_id}"),
        "runtime_surface": entry.get("runtime_surface"),
        "supports_resume": bool(entry.get("supports_resume")),
        "input_unit_label": entry.get("input_unit_label"),
        "template_version": entry.get("template_version"),
        "run_source": str(op.get("meta_mission_run_source") or "launcher").strip() or "launcher",
        "metrics": metrics,
        "last_run": metrics.get("last_run") if isinstance(metrics, Mapping) else None,
    }


def list_launchable_operations(repo_root: Path) -> Dict[str, Any]:
    try:
        operations = []
        for op in CATALOG:
            operation = {
                "operation_id": op["operation_id"],
                "label": op["label"],
                "kicker": op["kicker"],
                "description_short": op["description_short"],
                "command": op["command"],
                "parameters_schema": dict(op.get("parameters_schema") or {}),
                "dispatch_policy": _operation_dispatch_policy_payload(repo_root, op),
                "ui_group": op.get("ui_group"),
                "execution_mode": op.get("execution_mode") or "sync",
                "principle_refs": list(op.get("principle_refs") or []),
                "meta_mission": _operation_meta_mission_payload(repo_root, op),
            }
            if op.get("meta_mission_id"):
                operation["meta_mission_id"] = str(op.get("meta_mission_id") or "").strip()
                operation["meta_mission_run_source"] = (
                    str(op.get("meta_mission_run_source") or "launcher").strip()
                    or "launcher"
                )
            for compatibility_key in (
                "legacy_operation_ids",
                "canonical_operation_id",
                "legacy_alias",
            ):
                if compatibility_key in op:
                    operation[compatibility_key] = op[compatibility_key]
            if op["operation_id"] == "kernel_build_stale_phases":
                build_status = load_hologram_build_status(repo_root)
                operation["default_parameters"] = {
                    "phase_list": ",".join(build_status.get("stale_phase_ids") or [])
                }
            operations.append(operation)
        return {
            "operations": operations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"operations": [], "error": f"{type(exc).__name__}: {exc}"}


def _has_exact_apply_flag(command: str) -> bool:
    try:
        argv = shlex.split(command)
    except ValueError:
        return "--apply" in command.split()
    return any(arg == "--apply" for arg in argv)


def _render_optional_cli_flags(
    op: Mapping[str, Any],
    *,
    resolved: Mapping[str, str],
) -> tuple[list[str], str | None]:
    optional_flags = op.get("optional_cli_flags") if isinstance(op.get("optional_cli_flags"), Mapping) else {}
    rendered_fragments: list[str] = []
    for param_name, fragment_template in optional_flags.items():
        token = str(param_name or "").strip()
        if not token or not resolved.get(token):
            continue
        try:
            fragment = str(fragment_template or "").format(**resolved).strip()
        except KeyError as exc:
            return [], f"missing required parameter: {exc.args[0]}"
        if fragment:
            rendered_fragments.append(fragment)
    return rendered_fragments, None


def validate_and_render_command(
    op: Mapping[str, Any], parameters: Mapping[str, Any]
) -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
    schema = op.get("parameters_schema") or {}
    command_template = str(op.get("command") or "")
    parameters = _normalized_launch_parameters(op, parameters)
    resolved: Dict[str, str] = {}
    for name, spec in schema.items():
        required = bool(spec.get("required")) if isinstance(spec, Mapping) else False
        default = spec.get("default") if isinstance(spec, Mapping) else None
        raw_value = parameters.get(name) if parameters else None
        if raw_value is None or raw_value == "":
            if required and default is None:
                return None, f"missing required parameter: {name}", {}
            if default is not None:
                raw_value = default
            else:
                continue
        if not isinstance(raw_value, (str, int, float)):
            return None, f"parameter '{name}' must be a primitive (str/int/float)", {}
        str_value = str(raw_value).strip()
        if not str_value:
            if required:
                return None, f"parameter '{name}' cannot be empty", {}
            continue
        spec_type = str(spec.get("type") or "").strip().lower() if isinstance(spec, Mapping) else ""
        if spec_type == "integer":
            try:
                int_value = int(str_value)
            except ValueError:
                return None, f"parameter '{name}' must be an integer", {}
            minimum = spec.get("minimum") if isinstance(spec, Mapping) else None
            maximum = spec.get("maximum") if isinstance(spec, Mapping) else None
            if isinstance(minimum, (int, float)) and int_value < int(minimum):
                return None, f"parameter '{name}' must be >= {int(minimum)}", {}
            if isinstance(maximum, (int, float)) and int_value > int(maximum):
                return None, f"parameter '{name}' must be <= {int(maximum)}", {}
            resolved[name] = str(int_value)
            continue
        pattern = str(spec.get("pattern") or "").strip() if isinstance(spec, Mapping) else ""
        if pattern:
            if re.fullmatch(pattern, str_value) is None:
                return None, f"parameter '{name}' failed pattern validation", {}
        elif not LAUNCHABLE_PARAM_VALUE_RE.match(str_value):
            return (
                None,
                f"parameter '{name}' contains disallowed characters; only [A-Za-z0-9_./-] are allowed",
                {},
            )
        resolved[name] = str_value
    if parameters:
        unknown = [key for key in parameters.keys() if key not in schema]
        if unknown:
            return None, f"unknown parameters: {sorted(unknown)}", {}
    try:
        rendered = command_template.format(**resolved)
    except KeyError as exc:
        return None, f"missing required parameter: {exc.args[0]}", {}
    optional_fragments, fragment_error = _render_optional_cli_flags(op, resolved=resolved)
    if fragment_error:
        return None, fragment_error, {}
    if optional_fragments:
        rendered = " ".join([rendered, *optional_fragments]).strip()
    return rendered, None, resolved


def _normalize_nvidia_source_kinds(raw_value: Any) -> str:
    if raw_value is None or raw_value == "":
        return ""
    if isinstance(raw_value, str):
        raw_tokens = raw_value.split(",")
    elif isinstance(raw_value, Iterable) and not isinstance(raw_value, (bytes, bytearray)):
        raw_tokens = list(raw_value)
    else:
        raw_tokens = [raw_value]
    seen: set[str] = set()
    requested: list[str] = []
    allowed = set(NVIDIA_CONTINUOUS_SOURCE_ORDER)
    for raw_token in raw_tokens:
        token = str(raw_token or "").strip()
        if not token or token in seen or token not in allowed:
            continue
        seen.add(token)
        requested.append(token)
    order = {kind: index for index, kind in enumerate(NVIDIA_CONTINUOUS_SOURCE_ORDER)}
    return ",".join(sorted(requested, key=lambda kind: (order.get(kind, 999), kind)))


def _normalized_launch_parameters(
    op: Mapping[str, Any],
    parameters: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if str(op.get("operation_id") or "") != "nvidia_continuous_navigation_populate":
        return parameters or {}
    normalized = dict(parameters or {})
    source_kinds = _normalize_nvidia_source_kinds(normalized.get("source_kinds"))
    if source_kinds:
        normalized["source_kinds"] = source_kinds
    return normalized


def prepare_launch_operation(
    repo_root: Path,
    *,
    operation_id: str,
    parameters: Optional[Mapping[str, Any]] = None,
) -> PreparedLaunch:
    op = find_launchable_operation(operation_id or "")
    if not op:
        raise ValueError(f"unknown operation_id: {operation_id!r}")

    validation_policy = op.get("validation_policy") if isinstance(op, Mapping) else None
    if isinstance(validation_policy, Mapping) and validation_policy.get("dispatch_policy_mission_id"):
        schema = op.get("parameters_schema") if isinstance(op.get("parameters_schema"), Mapping) else {}
        provider_param = str(validation_policy.get("provider_param") or "provider")
        wave_param = str(validation_policy.get("wave_param") or "wave_width")
        provider_spec = schema.get(provider_param) if isinstance(schema, Mapping) else {}
        wave_spec = schema.get(wave_param) if isinstance(schema, Mapping) else {}

        raw_provider = (parameters or {}).get(provider_param)
        if raw_provider in (None, "") and isinstance(provider_spec, Mapping):
            raw_provider = provider_spec.get("default")
        raw_wave_width = (parameters or {}).get(wave_param)
        if raw_wave_width in (None, "") and isinstance(wave_spec, Mapping):
            raw_wave_width = wave_spec.get("default")

        provider = str(raw_provider or "chatgpt").strip() or "chatgpt"
        dispatch_policy_mission_id = str(validation_policy.get("dispatch_policy_mission_id") or "").strip()
        try:
            template = load_mission_template(repo_root, dispatch_policy_mission_id)
        except ValueError:
            template = load_mission_template(REPO_ROOT, dispatch_policy_mission_id)
        authored_dispatch_policy = (
            template.get("dispatch_policy")
            if isinstance(template.get("dispatch_policy"), Mapping)
            else {}
        )
        policy_resolution = resolve_dispatch_policy(
            mission_dispatch_policy={
                **dict(authored_dispatch_policy or {}),
                "mission_id": dispatch_policy_mission_id,
            },
            provider=provider,
            requested_wave_width=raw_wave_width,
            provider_capabilities_path=repo_root / "tools/meta/bridge/provider_capabilities.json",
        )
        if str(policy_resolution.get("status") or "").strip() != "ok":
            raise ValueError(
                f"{wave_param} {raw_wave_width} exceeds provider ceiling "
                f"{policy_resolution.get('provider_ceiling')} (provider-safe parallelism) "
                f"for provider '{provider}'"
            )

    command_template = str(op.get("command") or "")
    if _has_exact_apply_flag(command_template):
        raise ValueError("apply gate must go through kernel.py CLI directly, not the launch surface")
    command, error, resolved_parameters = validate_and_render_command(op, parameters or {})
    if error or not command:
        raise ValueError(error or "failed to render command")
    if _has_exact_apply_flag(command):
        raise ValueError("apply gate must go through kernel.py CLI directly, not the launch surface")
    return PreparedLaunch(
        operation=op,
        command=command,
        execution_mode=str(op.get("execution_mode") or "sync").strip().lower() or "sync",
        resolved_parameters=resolved_parameters,
    )


def start_meta_mission_run(
    repo_root: Path,
    *,
    prepared: PreparedLaunch,
    operation_id: str,
    parameters: Optional[Mapping[str, Any]] = None,
    trigger: str = "operator",
) -> Optional[str]:
    op = prepared.operation
    meta_mission_id = str(op.get("meta_mission_id") or "").strip()
    meta_mission_run_source = str(op.get("meta_mission_run_source") or "").strip()
    if not meta_mission_id or meta_mission_run_source != "launcher" or prepared.execution_mode != "sync":
        return None
    try:
        entry = _mmw.resolve_mission_entry(repo_root, meta_mission_id)
    except Exception:
        entry = None
    if entry is None:
        return None
    try:
        run_id = _mmw.mint_run_id(meta_mission_id, slug=f"op_{operation_id}")
        _mmw.start_run(
            repo_root,
            mission_id=meta_mission_id,
            run_id=run_id,
            trigger=trigger,
            provider=str((parameters or {}).get("provider") or "") or None,
            dispatch_policy_resolved=_operation_dispatch_policy_payload(repo_root, op),
            selection_summary={
                "operation_id": operation_id,
                "parameters": dict(parameters or {}),
            },
            template_version=str(entry.get("template_version") or "") or None,
            notes=f"Launched from {trigger} operation {operation_id}",
        )
        return run_id
    except Exception:
        return None


def finalize_meta_mission_run(
    repo_root: Path,
    *,
    prepared: PreparedLaunch,
    run_id: Optional[str],
    status: str,
    error: str | None = None,
    artifact_refs: list[str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    op = prepared.operation
    meta_mission_id = str(op.get("meta_mission_id") or "").strip()
    if not meta_mission_id or not run_id:
        return
    try:
        _mmw.finalize_run(
            repo_root,
            mission_id=meta_mission_id,
            run_id=run_id,
            status=status,
            error=error,
            artifact_refs=artifact_refs or None,
            extra=dict(extra or {}),
        )
    except Exception:
        return


def launcher_meta_mission_env(
    *,
    meta_mission_id: str,
    meta_mission_run_id: str | None,
    execution_mode: str,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(base_env or os.environ)
    if meta_mission_id and meta_mission_run_id and execution_mode == "sync":
        env["AIWF_META_MISSION_RUN_ID"] = meta_mission_run_id
        env["AIWF_META_MISSION_LIFECYCLE_OWNER"] = "launcher"
    return env


def _parse_operation_output_payload(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, Mapping):
        return dict(payload)

    decoder = json.JSONDecoder()
    for index in range(len(text) - 1, -1, -1):
        if text[index] != "{":
            continue
        try:
            payload, end_index = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping) and not text[index + end_index :].strip():
            return dict(payload)

    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{") or not candidate.endswith("}"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def parse_operation_output_payload(stdout: str) -> dict[str, Any]:
    return _parse_operation_output_payload(stdout)


def artifact_refs_from_operation_payload(payload: Mapping[str, Any]) -> list[str]:
    if not isinstance(payload, Mapping):
        return []

    refs: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                token = str(key or "").strip().lower()
                if isinstance(value, str) and token.endswith("_path") and value.strip():
                    refs.add(value.strip())
                    continue
                if isinstance(value, list):
                    if token.endswith("_paths"):
                        for item in value:
                            if isinstance(item, str) and item.strip():
                                refs.add(item.strip())
                        continue
                    for item in value:
                        visit(item)
                    continue
                if isinstance(value, Mapping):
                    visit(value)
            return
        if isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return sorted(refs)


def artifact_refs_from_operation_output(stdout: str) -> list[str]:
    return artifact_refs_from_operation_payload(parse_operation_output_payload(stdout))


def _event_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _compact_feed_readiness_status(value: Any) -> tuple[str, int]:
    if not isinstance(value, Mapping) or not value.get("present"):
        return "MISSING", 0
    ready = value.get("ready")
    blocker_count = int(value.get("blocker_count") or 0)
    if ready is True:
        return "READY", blocker_count
    if ready is False:
        return "BLOCKED", blocker_count
    return "UNKNOWN", blocker_count


def _compact_oracle_quartet_actions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    compact_actions: list[dict[str, Any]] = []
    for action in value:
        if not isinstance(action, Mapping):
            continue
        compact_actions.append(
            {
                "action_kind": str(action.get("action_kind") or "").strip(),
                "canonical_artifact_id": str(action.get("canonical_artifact_id") or "").strip(),
                "source_node_id": str(action.get("source_node_id") or "").strip(),
                "runner_target_id": str(action.get("runner_target_id") or "").strip(),
                "command": str(action.get("command") or "").strip(),
            }
        )
    return compact_actions


def _oracle_quartet_repair_event_field(payload: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("kind") or "").strip()
    if kind == "oracle_quartet_repair_plan":
        plan = payload
    elif kind in {"oracle_quartet_alias_materialization_receipt", "oracle_quartet_run_receipt"}:
        post_plan = payload.get("post_plan")
        plan = post_plan if isinstance(post_plan, Mapping) else {}
    else:
        return {}
    if not isinstance(plan, Mapping) or not plan:
        return {}

    readiness = plan.get("readiness")
    artifacts = plan.get("artifacts")
    status_counts: dict[str, int] = {}
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, Mapping):
                continue
            status = str(artifact.get("status") or "unknown").strip()
            status_counts[status] = status_counts.get(status, 0) + 1

    readiness_map = readiness if isinstance(readiness, Mapping) else {}
    return {
        "schema_version": "oracle_quartet_repair_summary_v1",
        "status": str(readiness_map.get("status") or "UNKNOWN").upper(),
        "subject_run_id": str(payload.get("subject_run_id") or plan.get("subject_run_id") or "").strip(),
        "truth_run_id": str(payload.get("truth_run_id") or plan.get("truth_run_id") or "").strip(),
        "result_kind": kind,
        "target": str(payload.get("target") or readiness_map.get("deepest_missing_target") or "").strip(),
        "deepest_missing_target": str(readiness_map.get("deepest_missing_target") or "").strip(),
        "missing_canonical_artifacts": _event_string_list(
            readiness_map.get("missing_canonical_artifacts")
        ),
        "aliasable_artifacts": _event_string_list(readiness_map.get("aliasable_artifacts")),
        "missing_source_nodes": _event_string_list(readiness_map.get("missing_source_nodes")),
        "status_counts": status_counts,
        "repair_actions": _compact_oracle_quartet_actions(plan.get("repair_actions")),
        "written_paths": _event_string_list(payload.get("written_paths")),
    }


def _evolve_input_readiness_event_field(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("kind") != "evolve_input_readiness":
        return {}

    readiness = payload.get("readiness")
    manifest = payload.get("manifest")
    if not isinstance(readiness, Mapping) or not isinstance(manifest, Mapping):
        return {}

    feed_health = manifest.get("feed_health")
    lab_cp2 = manifest.get("lab_cp2")
    subject_feed_readiness = manifest.get("subject_feed_readiness")
    truth_feed_readiness = manifest.get("truth_feed_readiness")
    repair_plan = payload.get("oracle_repair_plan")
    subject_run_id = str(
        payload.get("subject_run_id") or manifest.get("subject_run_id") or ""
    ).strip()
    truth_run_id = str(
        payload.get("truth_run_id") or manifest.get("truth_run_id") or ""
    ).strip()
    summary = {
        "schema_version": "evolve_input_readiness_summary_v1",
        "status": str(readiness.get("status") or "UNKNOWN").upper(),
        "subject_run_id": subject_run_id,
        "truth_run_id": truth_run_id,
        "feed_health_status": (
            str(feed_health.get("status") or "UNKNOWN").upper()
            if isinstance(feed_health, Mapping)
            else "UNKNOWN"
        ),
        "lab_cp2_status": (
            str(lab_cp2.get("status") or "unknown").strip().lower()
            if isinstance(lab_cp2, Mapping)
            else "unknown"
        ),
        "missing_artifacts": _event_string_list(manifest.get("missing_artifacts")),
        "blocking_reasons": _event_string_list(readiness.get("blocking_reasons")),
        "warnings": _event_string_list(readiness.get("warnings")),
    }
    subject_feed_status, subject_feed_blockers = _compact_feed_readiness_status(
        subject_feed_readiness
    )
    truth_feed_status, truth_feed_blockers = _compact_feed_readiness_status(
        truth_feed_readiness
    )
    summary["subject_feed_readiness_status"] = subject_feed_status
    summary["subject_feed_blocker_count"] = subject_feed_blockers
    summary["truth_feed_readiness_status"] = truth_feed_status
    summary["truth_feed_blocker_count"] = truth_feed_blockers
    if isinstance(repair_plan, Mapping):
        repair_readiness = repair_plan.get("readiness")
        if isinstance(repair_readiness, Mapping):
            summary["oracle_repair_status"] = str(
                repair_readiness.get("status") or "UNKNOWN"
            ).upper()
            deepest_target = str(repair_readiness.get("deepest_missing_target") or "").strip()
            if deepest_target:
                summary["oracle_deepest_missing_target"] = deepest_target
        repair_actions = repair_plan.get("repair_actions")
        if isinstance(repair_actions, list):
            summary["oracle_repair_actions"] = _compact_oracle_quartet_actions(repair_actions)
    return summary


def _lab_oracle_evolve_overnight_event_field(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("kind") != "lab_oracle_evolve_overnight_plan":
        return {}

    summary = payload.get("summary")
    budget = payload.get("budget")
    paths = payload.get("paths")
    selected_runs = payload.get("selected_runs")
    if not isinstance(summary, Mapping) or not isinstance(budget, Mapping):
        return {}

    compact_runs: list[dict[str, Any]] = []
    if isinstance(selected_runs, list):
        for row in selected_runs[:5]:
            if not isinstance(row, Mapping):
                continue
            compact_runs.append(
                {
                    "pair_id": str(row.get("pair_id") or "").strip(),
                    "subject_run_id": str(row.get("subject_run_id") or "").strip(),
                    "truth_run_id": str(row.get("truth_run_id") or "").strip(),
                    "readiness_status": str(row.get("readiness_status") or "UNKNOWN").upper(),
                    "estimated_cost_units": float(row.get("estimated_cost_units") or 0),
                    "command": str(row.get("command") or "").strip(),
                }
            )

    paths_map = paths if isinstance(paths, Mapping) else {}
    return {
        "schema_version": "lab_oracle_evolve_overnight_plan_summary_v1",
        "plan_id": str(payload.get("plan_id") or "").strip(),
        "provider": str(budget.get("provider") or "chatgpt").strip(),
        "budget_units": float(budget.get("budget_units") or 0),
        "selected_count": int(summary.get("selected_count") or 0),
        "eligible_count": int(summary.get("eligible_count") or 0),
        "skipped_count": int(summary.get("skipped_count") or 0),
        "estimated_spend_units": float(summary.get("estimated_spend_units") or 0),
        "remaining_budget_units": float(summary.get("remaining_budget_units") or 0),
        "plan_path": str(paths_map.get("plan_path") or "").strip() or None,
        "ledger_path": str(paths_map.get("ledger_path") or "").strip() or None,
        "selected_runs": compact_runs,
    }


def operation_event_fields_from_operation_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    result: dict[str, Any] = {}
    evolve_readiness = _evolve_input_readiness_event_field(payload)
    if evolve_readiness:
        result["evolve_input_readiness"] = evolve_readiness
    oracle_quartet_repair = _oracle_quartet_repair_event_field(payload)
    if oracle_quartet_repair:
        result["oracle_quartet_repair"] = oracle_quartet_repair
    overnight_plan = _lab_oracle_evolve_overnight_event_field(payload)
    if overnight_plan:
        result["lab_oracle_evolve_overnight_plan"] = overnight_plan
    summary = payload.get("result_summary")
    if isinstance(summary, Mapping):
        result["result_summary"] = dict(summary)
    stable_signal_digest = str(payload.get("stable_signal_digest") or "").strip()
    if stable_signal_digest:
        result["stable_signal_digest"] = stable_signal_digest
    route_evidence = payload.get("route_evidence")
    if isinstance(route_evidence, list):
        filtered: list[dict[str, Any]] = []
        for item in route_evidence:
            if not isinstance(item, Mapping):
                continue
            source = str(item.get("source_artifact") or item.get("source") or "").strip()
            target = str(item.get("target_artifact") or item.get("target") or "").strip()
            if not source or not target:
                continue
            filtered.append(dict(item))
        if filtered:
            result["route_evidence"] = filtered
    return result


def operation_event_fields_from_operation_output(stdout: str) -> dict[str, Any]:
    return operation_event_fields_from_operation_payload(parse_operation_output_payload(stdout))
