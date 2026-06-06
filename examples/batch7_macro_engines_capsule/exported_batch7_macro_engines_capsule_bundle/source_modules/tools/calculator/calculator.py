"""
[PURPOSE]
- Teleology: Convert raw asset feeds into regime-aware cluster intelligence that is useful for sizing, focus, and narrative extraction.
- Mechanism: Project JSON artifacts into Pandas DataFrames, aggregate configured metrics, apply size-aware shrinkage plus robust lane normalization, then rank groups by directional thesis quality rather than raw magnitude alone.
- Hardening: Handles missing data gracefully, enforces configurable precision, and ensures schema compliance via an Output Envelope.
[INTERFACE]
- Reads: `config` (dict) defining metrics and file paths.
- Reads: `stock_feed`, `macro_feed`, and `etf_feed` JSON artifacts from the filesystem.
- Returns: Output Envelope (`dict`) containing ranked groups for Stock, Macro, and ETF vectors.
- Schema: Output Envelope
    - `metadata`: {status, run_id, as_of, legend, items_count}
    - `data`: {stock: [[group, {Energy, Polarity, Directional_Concentration, Dominant_Signal, members, metrics...}], ...], macro: ..., etf: ...}
[FLOW]
1.  **Hydrate:** `StandardActor` initializes with config, resolving paths and metric specifications.
2.  **Ingest:** Loads JSON artifacts (`global_stock_feed`, `global_macro_feed`, `global_etf_feed`) from the run directory.
3.  **Project:** Converts raw JSON rows/columns into Pandas DataFrames.
4.  **Aggregate:** Groups data by sector/proxy, computes configured metrics, and regularizes those aggregates with empirical shrinkage.
5.  **Profile:** Builds a signal profile from robust cross-sectional normalization and member-level cohesion geometry.
6.  **Rank:** Sorts groups by opportunity / thesis quality descending.
7.  **Truncate:** Applies `top_n_rank` limit if configured.
8.  **Envelope:** Wraps results in a standardized success/failure dictionary.
[DEPENDENCIES]
- pypi.pandas: DataFrame aggregation / column projection
- pypi.numpy: vector math, norms, robust scaling helpers
- data.tools.stock: stock_feed (dependency)
- data.tools.macro: macro_feed (dependency)
[CONSTRAINTS]
- Precision: All float outputs rounded to configured precision (default 4).
- Resilience: Execution catches all internal exceptions and returns a "failure" envelope rather than crashing.
- I/O: Pure function behavior regarding output; returns payload to caller, does not write to disk.
- When-needed: Open when a market-intelligence workflow needs the cross-lane calculator that fuses stock, macro, and ETF feeds into ranked group intelligence.
- Escalates-to: tools/macro/macro.py::run; tools/oracle/subject_index.py::run
- Navigation-group: market_intelligence
"""

from __future__ import annotations

import json
import logging
import hashlib
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple, Set

import numpy as np
import pandas as pd
from system.lib import feed_envelope
from system.lib.types import TOOL_METADATA_SCHEMA_VERSION
from system.lib.artifacts import load_artifact

logger = logging.getLogger(__name__)

# --- PHASE 2 CONSTANTS ---
LEGEND = {
    "Energy": "Weighted L2 norm of the post-shrinkage, post-normalization metric vector.",
    "Polarity": "Signed sum of directional factors only; positive = net pro-risk / upside, negative = defensive / downside.",
    "Directional_Concentration": "Directional agreement among directional factors only; 0=mixed, 1=fully aligned.",
    "Dominant_Signal": "Metric key with highest weighted abs(z); what is actually driving the cluster after factor weighting.",
    "Size": "Count of members in group",
    "members": "List of tickers/IDs in this group",
    "metrics_raw": "Aggregated stats per group config (post-imputation, pre-normalization)",
    "metrics_norm": "Lane-normalized stats per group after empirical shrinkage and robust scaling.",
    "metrics": "Condensed thesis-quality summary metrics intended for table display.",
    "Opportunity_Score": "Final rank score combining thrust, purity, member consensus, and effective breadth-adjusted size.",
    "Purity": "Share of signal energy coming from directional factors rather than dispersion, risk, or structural noise.",
    "Cohesion": "Mean cosine alignment of member directional vectors to the cluster centroid.",
    "Participation_Rate": "Share of members aligned with the cluster centroid.",
    "Effective_Breadth": "Inverse-Herfindahl breadth of member contribution to the active thesis.",
    "Directional_Balance": "Inverse-Herfindahl breadth across directional factor contributions; high means the thesis is multi-factor rather than single-driver.",
    "Directional_Reach": "Continuous activation strength across directional factors relative to the lane clip ceiling.",
    "rank_method": "Opportunity_Score descending, then Energy descending (Top-N truncated)",
    "groups": "Market sectors (Stock), ETF categories, or Macro proxies"
}
TOOL_NAME = "calculator"
DATA_SCHEMA_VERSION = "calculator.6"
FORECAST_CARD_SCHEMA_VERSION = "forecast_claim_card_v0"
EXPLAIN_PAYLOAD_SCHEMA_VERSION = "calculator_explain_payload_v0"

STRUCTURAL_METRIC_HINTS = ("price_level", "price_dispersion", "sample_size")
DISPERSION_METRIC_HINTS = ("dispersion",)
RISK_METRIC_HINTS = ("vol_", "volatility")
PROFILE_WEIGHTS = {
    "directional": 1.0,
    "risk": 0.75,
    "dispersion": 0.65,
    "structural": 0.35,
}
VALID_METRIC_BUCKETS = set(PROFILE_WEIGHTS.keys())
MAD_SCALE = 1.4826
EPSILON = 1e-12
SHRINKAGE_PRIORS = {
    "directional": 6.0,
    "risk": 8.0,
    "dispersion": 9.0,
    "structural": 12.0,
}
EFFECTIVE_SIZE_PRIOR = 8.0


class LogicalFailure(Exception):
    """
    [ROLE]
    - Teleology: Signal a non-recoverable logical contract violation inside the calculator pipeline.
    - Ownership: Owns no state; raised and caught within StandardActor.execute().
    - Mutability: Immutable (Exception subclass with no additional attributes).
    - Concurrency: Not applicable; thrown and caught within a single call stack.
    """


@dataclass
class MetricSpec:
    """
    [ROLE]
    - Teleology: Carry the per-metric aggregation specification that StandardActor uses to project DataFrames into group-level statistics.
    - Ownership: Owns its key, column list, aggregation op, and scale scalar; instantiated and owned by StandardActor._parse_metrics().
    - Mutability: Mutable dataclass; treated as effectively immutable after construction.
    - Concurrency: Not shared across threads; each StandardActor instance owns its own list.
    """

    key: str
    columns: List[str]
    op: str
    scale: float = 1.0
    bucket: Optional[str] = None
    description: Optional[str] = None


class StandardActor:
    """
    [ROLE]
    - Teleology: Execute the full cross-lane calculator pipeline that fuses stock, macro, and ETF feeds into ranked group intelligence.
    - Ownership: Owns the resolved config, run directory, metric specs, and runtime parameters for one execution unit.
    - Mutability: Mutable during __init__; treated as effectively immutable once constructed; execute() is a one-shot call.
    - Concurrency: Not thread-safe; one instance per run, not shared across threads.
    """

    def __init__(self, config: Dict[str, Any], run_dir: Path) -> None:
        """
        [ACTION]
        Initializes the actor with configuration and path resolution.

        - **Preconditions:** `config` must be a valid dictionary. `run_dir` should be a Path object.
        - **Logic:** Unwraps data/config layers, resolves input file paths, and parses metric specs.
        - **Reads:** `config` for precision, metric definitions, and column mappings.
        - **Orders:** Parses metrics lists into `MetricSpec` objects.
        """
        # 1. Universal Config Unwrap
        self.config = config.get("data", config) if isinstance(config, dict) else {}
        self.run_dir = run_dir

        # 2. Resolve Paths
        self.stock_path = self.config.get("stock_feed", "global_stock_feed.json")
        self.macro_path = self.config.get("macro_feed", "global_macro_feed.json")
        self.etf_path = self.config.get("etf_feed", "global_etf_feed.json")

        # Note: 'output' config key is ignored; Engine handles persistence.

        self.group_col_stock = self.config.get("group_col_stock", "Category")
        self.group_col_macro = self.config.get("group_col_macro", "Proxy")
        self.group_col_etf = self.config.get("group_col_etf", "Category")

        # 3. Resolve Logic Params
        cfg_inner = self.config.get("config", {})
        self.precision = cfg_inner.get("precision", 4)
        self.imputation_policy = cfg_inner.get("imputation_policy", "lane_median_then_zero")
        self.normalization_policy = cfg_inner.get("normalization_policy", "robust_zscore")
        self.normalization_clip = float(cfg_inner.get("normalization_clip", 3.0))
        self.energy_policy = cfg_inner.get("energy_policy", "from_metrics_norm")
        self.forecast_card_count = int(
            cfg_inner.get("forecast_card_count")
            or self.config.get("forecast_card_count")
            or self.config.get("top_n_rank")
            or cfg_inner.get("top_n_rank")
            or self.config.get("top_n")
            or cfg_inner.get("top_n")
            or 10
        )
        horizons_raw = (
            cfg_inner.get("forecast_card_horizons")
            or self.config.get("forecast_card_horizons")
            or ["next_configured_horizon"]
        )
        self.forecast_card_horizons = [
            str(item).strip()
            for item in (horizons_raw if isinstance(horizons_raw, list) else [horizons_raw])
            if str(item).strip()
        ] or ["next_configured_horizon"]
        self.metric_bucket_overrides: Dict[str, str] = {}
        self.metric_descriptions: Dict[str, str] = {}
        
        self.metrics_stock = self._parse_metrics(self.config.get("stock_metrics", []))
        self.metrics_macro = self._parse_metrics(self.config.get("macro_metrics", []))
        self.metrics_etf = self._parse_metrics(self.config.get("etf_metrics", []))

        if not self.metrics_stock and "metrics" in self.config:
            self.metrics_stock = self._parse_metrics(self.config.get("metrics", []))
        # ETF falls back to stock metrics if not explicitly defined
        if not self.metrics_etf:
            self.metrics_etf = self.metrics_stock
        self._index_metric_semantics(self.metrics_stock, self.metrics_macro, self.metrics_etf)

        self.top_n = (
            self.config.get("top_n_rank")
            or cfg_inner.get("top_n_rank")
            or self.config.get("top_n")
            or cfg_inner.get("top_n")
            or 0
        )

        # 4. Runtime Context
        runtime = self.config.get("runtime", {})
        self.run_id = runtime.get("run_id") or self.run_dir.name
        self.as_of = runtime.get("as_of") or runtime.get("time_anchor") or datetime.now(timezone.utc).isoformat()

    def _metric_semantic_key(self, metric_key: str) -> str:
        return str(metric_key or "").strip().lower()

    def _normalize_metric_bucket(self, value: Any) -> Optional[str]:
        bucket = str(value or "").strip().lower()
        return bucket if bucket in VALID_METRIC_BUCKETS else None

    def _index_metric_semantics(self, *metric_groups: List[MetricSpec]) -> None:
        for metrics in metric_groups:
            for spec in metrics:
                key = self._metric_semantic_key(spec.key)
                if not key:
                    continue
                if spec.bucket:
                    self.metric_bucket_overrides[key] = spec.bucket
                if spec.description:
                    self.metric_descriptions[key] = spec.description

    def _metric_bucket(self, metric_key: str) -> str:
        """
        [ACTION]
        Classifies metrics into directional, risk, dispersion, or structural buckets.

        - **Goal:** Prevent size/price plumbing metrics from overpowering actionable market thrust.
        """
        key = str(metric_key or "").strip().lower()
        if not key:
            return "directional"
        explicit = self.metric_bucket_overrides.get(key)
        if explicit:
            return explicit
        if any(hint in key for hint in STRUCTURAL_METRIC_HINTS):
            return "structural"
        if any(hint in key for hint in RISK_METRIC_HINTS):
            return "risk"
        if any(hint in key for hint in DISPERSION_METRIC_HINTS):
            return "dispersion"
        return "directional"

    def _metric_weight(self, metric_key: str) -> float:
        return float(PROFILE_WEIGHTS.get(self._metric_bucket(metric_key), 1.0))

    def _safe_norm(self, values: List[float]) -> float:
        if not values:
            return 0.0
        return float(np.linalg.norm(np.array(values, dtype=float)))

    def _safe_sqrt(self, value: float) -> float:
        return float(np.sqrt(max(value, 0.0)))

    def _clip01(self, value: float) -> float:
        return float(np.clip(value, 0.0, 1.0))

    def _effective_breadth_score(self, values: List[float]) -> float:
        weights = [abs(float(value)) for value in values if abs(float(value)) > EPSILON]
        if not weights:
            return 0.0
        denom = float(sum(weight * weight for weight in weights))
        if denom < EPSILON:
            return 0.0
        return self._clip01((sum(weights) ** 2) / (len(weights) * denom))

    def _metric_prior_strength(self, metric_key: str) -> float:
        return float(SHRINKAGE_PRIORS.get(self._metric_bucket(metric_key), SHRINKAGE_PRIORS["directional"]))

    def _compute_center_scale(self, arr: np.ndarray) -> Tuple[float, float]:
        if arr.size == 0:
            return 0.0, 0.0

        policy = str(self.normalization_policy or "robust_zscore").strip().lower()
        if policy == "zscore" or arr.size < 5:
            center = float(arr.mean())
            scale = float(arr.std(ddof=0))
            return center, scale

        center = float(np.median(arr))
        mad = float(np.median(np.abs(arr - center)))
        scale = float(MAD_SCALE * mad)
        if scale < EPSILON and arr.size >= 2:
            q75, q25 = np.percentile(arr, [75, 25])
            scale = float((q75 - q25) / 1.349) if abs(q75 - q25) > EPSILON else 0.0
        if scale < EPSILON:
            scale = float(arr.std(ddof=0))
        return center, scale

    def _directional_source_columns(self, metrics: List[MetricSpec], df: pd.DataFrame) -> List[str]:
        columns: List[str] = []
        for spec in metrics:
            if self._metric_bucket(spec.key) != "directional":
                continue
            for column in spec.columns:
                if column in df.columns and column not in columns:
                    columns.append(column)
        return columns

    def _build_directional_feature_stats(
        self, df: pd.DataFrame, metrics: List[MetricSpec]
    ) -> Dict[str, Tuple[float, float]]:
        stats: Dict[str, Tuple[float, float]] = {}
        for column in self._directional_source_columns(metrics, df):
            s = self._impute_lane(pd.to_numeric(df[column], errors="coerce"))
            arr = s.to_numpy(dtype=float)
            _, scale = self._compute_center_scale(arr)
            # Directional source columns are economically centered at zero; using the
            # lane median here would make broad positive groups look internally mixed.
            stats[column] = (0.0, float(scale if scale > EPSILON else 1.0))
        return stats

    def _compute_member_profile(
        self,
        g: pd.DataFrame,
        feature_stats: Dict[str, Tuple[float, float]],
    ) -> Dict[str, float]:
        if not feature_stats:
            return {
                "Cohesion": 0.0,
                "Participation_Rate": 0.0,
                "Effective_Breadth": 0.0,
            }

        columns = [column for column in feature_stats if column in g.columns]
        if not columns:
            return {
                "Cohesion": 0.0,
                "Participation_Rate": 0.0,
                "Effective_Breadth": 0.0,
            }

        vectors = []
        for column in columns:
            center, scale = feature_stats[column]
            s = self._impute_lane(pd.to_numeric(g[column], errors="coerce"))
            vectors.append(((s - center) / max(scale, 1.0)).to_numpy(dtype=float))

        if not vectors:
            return {
                "Cohesion": 0.0,
                "Participation_Rate": 0.0,
                "Effective_Breadth": 0.0,
            }

        x = np.column_stack(vectors)
        size = int(x.shape[0])
        if size <= 0:
            return {
                "Cohesion": 0.0,
                "Participation_Rate": 0.0,
                "Effective_Breadth": 0.0,
            }
        if size == 1:
            return {
                "Cohesion": 1.0,
                "Participation_Rate": 1.0,
                "Effective_Breadth": 1.0,
            }

        centroid = np.mean(x, axis=0)
        centroid_norm = float(np.linalg.norm(centroid))
        if centroid_norm < EPSILON:
            return {
                "Cohesion": 0.0,
                "Participation_Rate": 0.0,
                "Effective_Breadth": 0.0,
            }

        cosines: List[float] = []
        weights: List[float] = []
        for row in x:
            row_norm = float(np.linalg.norm(row))
            if row_norm < EPSILON:
                cosine = 0.0
            else:
                cosine = float(np.clip(np.dot(row, centroid) / (row_norm * centroid_norm), -1.0, 1.0))
            projection = float(abs(np.dot(row, centroid)) / centroid_norm) if centroid_norm > EPSILON else 0.0
            cosines.append(cosine)
            weights.append(max(0.0, cosine) * projection)

        participation = float(sum(1 for cosine in cosines if cosine > 0.0) / len(cosines))
        denom = float(sum(weight * weight for weight in weights))
        effective_breadth = 0.0
        if denom > EPSILON:
            effective_breadth = float((sum(weights) ** 2) / (len(weights) * denom))

        return {
            "Cohesion": round(self._clip01(max(0.0, float(np.mean(cosines)))), self.precision),
            "Participation_Rate": round(self._clip01(participation), self.precision),
            "Effective_Breadth": round(self._clip01(effective_breadth), self.precision),
        }

    def _parse_metrics(self, metrics: List[Dict[str, Any]]) -> List[MetricSpec]:
        """
        [ACTION]
        Parses raw dictionary metric configurations into typed MetricSpecs.

        - **Transformation:** Converts dictionary keys to MetricSpec attributes.
        - **Fails:** Log warning -> Skips item if validation fails.
        - **Returns:** List of valid `MetricSpec` objects.
        """
        out: List[MetricSpec] = []
        for m in metrics:
            try:
                description = m.get("description")
                out.append(
                    MetricSpec(
                        key=str(m.get("key")),
                        columns=list(m.get("columns", [])),
                        op=str(m.get("op", "mean")).lower(),
                        scale=float(m.get("scale", 1.0)),
                        bucket=self._normalize_metric_bucket(m.get("bucket")),
                        description=description.strip() if isinstance(description, str) and description.strip() else None,
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping invalid metric spec {m}: {e}")
        return out

    def _metric_semantics_payload(self) -> Dict[str, Any]:
        """
        [ACTION]
        Emits metric semantics alongside the feed so frontend consumers do not
        duplicate bucket or description authority.
        """
        payload: Dict[str, Any] = {}
        seen: Set[str] = set()
        for spec in [*self.metrics_stock, *self.metrics_macro, *self.metrics_etf]:
            if spec.key in seen:
                continue
            seen.add(spec.key)
            payload[spec.key] = {
                "bucket": self._metric_bucket(spec.key),
                "bucket_source": "config" if spec.bucket else "heuristic_name_hint",
                "columns": list(spec.columns),
                "op": spec.op,
                "scale": spec.scale,
            }
            description = self.metric_descriptions.get(self._metric_semantic_key(spec.key))
            if description:
                payload[spec.key]["description"] = description
        return payload

    def _load_json_artifact(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        [ACTION]
        Loads a JSON artifact from the run directory or artifacts subdirectory.

        - **Reads:** Delegates to system.lib.artifacts.load_artifact which tries
          run_dir/artifacts/{node_id}.json then run_dir/{node_id}.json.
        - **Guarantee:** Returns parsed Dict if found and valid.
        - **Fails:** File not found or JSON decode error -> Returns None.
        - **Reads:** Standard Python I/O via shared artifact utility.
        """
        node_id = Path(filename).stem
        result = load_artifact(self.run_dir, node_id)
        if result is None:
            logger.warning(f"Artifact {filename} not found in {self.run_dir}")
        return result

    def _parse_matrix(self, payload: Dict[str, Any], flavor: str) -> pd.DataFrame:
        """
        [ACTION]
        Converts a row-column JSON structure into a Pandas DataFrame.

        - **Preconditions:** Payload must contain "data" dict with "rows" and "columns".
        - **Transformation:** Normalizes column names (e.g., 'slug' -> 'ticker' for macro).
        - **Fails:** Missing keys or shape mismatch -> Returns empty DataFrame (logs error).
        """
        data = payload.get("data", payload)
        if isinstance(data, dict):
            cols = data.get("columns")
            rows = data.get("rows")
            if isinstance(cols, list) and isinstance(rows, list):
                try:
                    df = pd.DataFrame(rows, columns=cols)
                    if flavor == "macro":
                        if "slug" in df.columns and "ticker" not in df.columns:
                            df = df.rename(columns={"slug": "ticker"})
                    return df
                except Exception as e:
                    logger.error(f"Failed to create DataFrame ({flavor}): {e}")
        return pd.DataFrame()

    def _impute_lane(self, series: pd.Series) -> pd.Series:
        """
        [ACTION]
        Deterministic imputation: replaces NaN with lane median, then zero for any remaining.

        - **Policy:** lane_median_then_zero (locked per C2 spec).
        - **Guarantee:** Returns a Series with no NaN values.
        """
        if series.isna().any():
            median_val = series.median()
            if pd.isna(median_val):
                median_val = 0.0
            series = series.fillna(median_val)
        # Final zero-fill for any remaining NaN (edge case: empty series median is NaN)
        return series.fillna(0.0)

    def _normalize_groups_cross_sectional(
        self, groups: Dict[str, Any]
    ) -> None:
        """
        [ACTION]
        Applies cross-group (lane-wide) z-score normalization for each metric.

        - **Input:** Dict of group_name -> group payload.
        - **Logic:** Compute mean/std of all non-None values for each metric across groups;
                     apply (v - mean)/std with clip.
        - **Degenerate cases:** If std == 0 or < 2 values, sets 0.0.
        """
        metric_keys = set()
        for group in groups.values():
            metric_keys.update(group["metrics_raw"].keys())
        
        for key in metric_keys:
            group_vals = []
            raw_values = []
            for group_name, group_data in groups.items():
                val = group_data["metrics_raw"].get(key)
                if isinstance(val, (int, float)):
                    raw_values.append(float(val))
                    group_vals.append((group_name, float(val)))

            if len(group_vals) < 2:
                for group_name, _ in group_vals:
                    groups[group_name]["metrics_norm"][key] = 0.0
                continue

            prior_center = float(np.median(np.array(raw_values, dtype=float)))
            adjusted_vals = []
            for group_name, raw_val in group_vals:
                size = max(int(groups[group_name].get("Size", 0)) - 1, 0)
                prior_strength = self._metric_prior_strength(key)
                shrink = self._safe_sqrt(size / float(size + prior_strength)) if size > 0 else 0.0
                adjusted_val = prior_center + shrink * (raw_val - prior_center)
                adjusted_vals.append((group_name, adjusted_val))

            arr = np.array([v for _, v in adjusted_vals], dtype=float)
            center, scale = self._compute_center_scale(arr)
            if scale < EPSILON:
                for group_name, _ in adjusted_vals:
                    groups[group_name]["metrics_norm"][key] = 0.0
                continue

            for group_name, v in adjusted_vals:
                z = (v - center) / scale
                z = float(np.clip(z, -self.normalization_clip, self.normalization_clip))
                groups[group_name]["metrics_norm"][key] = round(z, self.precision)

    def _identify_ticker_col(self, df: pd.DataFrame) -> Optional[str]:
        """
        [ACTION]
        Heuristically identifies the column containing ticker symbols.

        - **Logic:** Checks for known candidate column names.
        - **Returns:** First matching column name or None.
        """
        candidates = ["ticker", "Ticker", "symbol", "Symbol", "slug", "id"]
        for c in candidates:
            if c in df.columns:
                return c
        return None

    def _compute_group_metrics(
        self, df: pd.DataFrame, group_col: str, metrics: List[MetricSpec]
    ) -> Tuple[Dict[str, Any], int]:
        """
        [ACTION]
        Aggregates DataFrame rows into grouped metrics with imputation + lane normalization.

        - **Preconditions:** `df` must not be empty; `group_col` must exist.
        - **Logic:**
            1. Group by `group_col`.
            2. Extract members list.
            3. Impute NaN values per spec before computing stats.
            4. Compute stats per MetricSpec → metrics_raw.
            5. Apply cross-sectional z-score normalization → metrics_norm.
            6. Compute L2 Norm Energy from metrics_norm.
        - **Returns:** (groups dict, total_nan_count_before_imputation).
        """
        results: Dict[str, Any] = {}
        total_nan_count = 0
        if df.empty or group_col not in df.columns:
            return results, 0

        gdf = df.copy()
        gdf[group_col] = gdf[group_col].fillna("Unknown")

        if gdf.empty:
            return results, 0

        ticker_col = self._identify_ticker_col(df)
        feature_stats = self._build_directional_feature_stats(gdf, metrics)

        for group_name, g in gdf.groupby(group_col):
            group_name_str = str(group_name)

            # 1. Extract Members
            members = []
            if ticker_col:
                members = sorted(g[ticker_col].fillna("Unknown").astype(str).unique().tolist())

            entry: Dict[str, Any] = {
                "Size": int(len(g)),
                "members": members,
                "metrics_raw": {},
                "metrics_norm": {},
                "_member_profile": self._compute_member_profile(g, feature_stats),
            }

            # 2. Compute Metrics (with imputation — no silent dropna)
            if not metrics:
                numeric_cols = g.select_dtypes(include=[np.number]).columns.tolist()
                # Count NaNs before imputation for diagnostics.
                for c in numeric_cols:
                    total_nan_count += int(g[c].isna().sum())
                entry["metrics_raw"] = self._basic_stats_imputed(g, numeric_cols)
            else:
                for spec in metrics:
                    for c in spec.columns:
                        if c in g.columns:
                            total_nan_count += int(g[c].isna().sum())
                    value = self._compute_metric_imputed(g, spec)
                    entry["metrics_raw"][spec.key] = value

            results[group_name_str] = entry

        # 3. Lane-local cross-sectional normalization → metrics_norm
        self._normalize_groups_cross_sectional(results)

        # 4. Compute Signal Profile from metrics_norm (per C2 spec + Tier 1 upgrade).
        for entry in results.values():
            member_profile = entry.pop("_member_profile", None)
            profile = self._compute_signal_profile(
                entry["metrics_norm"],
                int(entry.get("Size", 0)),
                member_profile if isinstance(member_profile, dict) else None,
            )
            entry.update(profile)

        return results, total_nan_count

    def _basic_stats_imputed(self, g: pd.DataFrame, cols: List[str]) -> Dict[str, Any]:
        """
        [ACTION]
        Computes default mean/std stats after imputation (no silent NaN drops).
        """
        out: Dict[str, Any] = {}
        for c in cols:
            s = self._impute_lane(pd.to_numeric(g[c], errors="coerce"))
            out[c] = {
                "mean": round(float(s.mean()), self.precision),
                "std": round(float(s.std(ddof=0)), self.precision) if len(s) > 1 else 0.0
            }
        return out

    def _compute_metric_imputed(self, g: pd.DataFrame, spec: MetricSpec) -> Any:
        """
        [ACTION]
        Computes a specific metric aggregation with deterministic imputation.

        - **Transformation:** Extracts columns → Imputes NaN → Flattens to array → Applies op → Scales.
        - **Returns:** Rounded float value or 0.0 (never None — imputation ensures data).
        """
        vals: List[float] = []
        for c in spec.columns:
            if c not in g.columns:
                continue
            s = self._impute_lane(pd.to_numeric(g[c], errors="coerce"))
            vals.extend([float(x) for x in s.values.tolist()])

        if not vals:
            return 0.0  # No matching columns at all — return zero, not None.

        arr = np.array(vals, dtype=float)
        op = spec.op

        if op == "mean": res = float(arr.mean())
        elif op == "sum": res = float(arr.sum())
        elif op == "max": res = float(arr.max())
        elif op == "min": res = float(arr.min())
        elif op in ("std", "stdev"): res = float(arr.std(ddof=0)) if arr.size > 1 else 0.0
        elif op == "median": res = float(np.median(arr))
        else: res = float(arr.mean())

        return round(res * spec.scale, self.precision)

    def _compute_signal_profile(
        self,
        metrics_norm: Dict[str, Any],
        size: int,
        member_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        [ACTION]
        Computes the full Signal Profile from the group's normalized metric vector.

        - **Input:** metrics_norm dict (post-lane-normalization, z-score values).
        - **Returns:** Dict with top-level signal fields plus a condensed `metrics` summary block.
        - **Guarantee:** Always operates on normalized values (no cross-lane magnitude dominance).
        """
        valid = [(k, float(v)) for k, v in metrics_norm.items() if isinstance(v, (int, float))]
        if not valid:
            return {
                "Energy": 0.0,
                "Polarity": 0.0,
                "Directional_Concentration": 0.0,
                "Dominant_Signal": "None",
                "metrics": {
                    "Opportunity_Score": 0.0,
                    "Thrust_Score": 0.0,
                    "Directional_Energy": 0.0,
                    "Dispersion_Energy": 0.0,
                    "Risk_Energy": 0.0,
                    "Structural_Energy": 0.0,
                    "Directional_Share": 0.0,
                    "Directional_Breadth": 0.0,
                    "Directional_Balance": 0.0,
                    "Directional_Reach": 0.0,
                    "Purity": 0.0,
                    "Cohesion": 0.0,
                    "Participation_Rate": 0.0,
                    "Effective_Breadth": 0.0,
                    "Effective_Size": 0.0,
                    "Signal_Quality": 0.0,
                    "Size_Confidence": 0.0,
                    "Dominant_Z": 0.0,
                },
            }

        weighted: List[Tuple[str, float, str]] = []
        directional_vals: List[float] = []
        dispersion_vals: List[float] = []
        risk_vals: List[float] = []
        structural_vals: List[float] = []

        for key, raw_val in valid:
            bucket = self._metric_bucket(key)
            weighted_val = raw_val * self._metric_weight(key)
            weighted.append((key, weighted_val, bucket))
            if bucket == "directional":
                directional_vals.append(weighted_val)
            elif bucket == "dispersion":
                dispersion_vals.append(weighted_val)
            elif bucket == "risk":
                risk_vals.append(weighted_val)
            else:
                structural_vals.append(weighted_val)

        weighted_nums = [value for _, value, _ in weighted]
        energy = self._safe_norm(weighted_nums)
        directional_energy = self._safe_norm(directional_vals)
        dispersion_energy = self._safe_norm(dispersion_vals)
        risk_energy = self._safe_norm(risk_vals)
        structural_energy = self._safe_norm(structural_vals)

        polarity = float(sum(directional_vals))
        q_dir = len(directional_vals)
        concentration = 0.0
        if directional_energy > 0.0 and q_dir > 0:
            concentration = abs(polarity) / (np.sqrt(q_dir) * directional_energy)

        active_directional = sum(1 for value in directional_vals if abs(value) >= 0.75)
        directional_breadth = float(active_directional / q_dir) if q_dir > 0 else 0.0
        directional_breadth = self._clip01(directional_breadth)
        directional_balance = self._effective_breadth_score(directional_vals)
        directional_reach = (
            float(np.mean([min(abs(value) / max(self.normalization_clip, 1.0), 1.0) for value in directional_vals]))
            if directional_vals
            else 0.0
        )
        directional_reach = self._clip01(directional_reach)

        member_profile = member_profile or {}
        cohesion = self._clip01(float(member_profile.get("Cohesion", 0.0) or 0.0))
        participation_rate = self._clip01(float(member_profile.get("Participation_Rate", 0.0) or 0.0))
        effective_breadth = self._clip01(float(member_profile.get("Effective_Breadth", 0.0) or 0.0))

        effective_size = float(max(size - 1, 0)) * (0.5 + 0.5 * participation_rate) * (0.35 + 0.65 * effective_breadth)
        size_confidence = self._safe_sqrt(effective_size / float(effective_size + EFFECTIVE_SIZE_PRIOR)) if effective_size > 0.0 else 0.0
        directional_share = float(directional_energy / energy) if energy > 0.0 else 0.0
        purity_denom = directional_energy + (0.85 * dispersion_energy) + (0.65 * risk_energy) + (0.75 * structural_energy)
        purity = float(directional_energy / purity_denom) if purity_denom > 0.0 else 0.0
        member_quality = self._safe_sqrt(cohesion * participation_rate)
        thrust_score = directional_energy * concentration * (
            0.2
            + (0.35 * directional_breadth)
            + (0.25 * directional_balance)
            + (0.20 * directional_reach)
        )
        signal_quality = self._safe_sqrt(purity * member_quality * max(size_confidence, 0.0))
        opportunity_score = (
            thrust_score
            * purity
            * (0.15 + 0.85 * member_quality)
            * (0.25 + 0.75 * size_confidence)
        )

        dominant_key, dominant_z, _ = max(weighted, key=lambda item: abs(item[1]))

        return {
            "Energy": round(energy, self.precision),
            "Polarity": round(polarity, self.precision),
            "Directional_Concentration": round(float(concentration), self.precision),
            "Dominant_Signal": dominant_key,
            "metrics": {
                "Opportunity_Score": round(float(opportunity_score), self.precision),
                "Thrust_Score": round(float(thrust_score), self.precision),
                "Directional_Energy": round(float(directional_energy), self.precision),
                "Dispersion_Energy": round(float(dispersion_energy), self.precision),
                "Risk_Energy": round(float(risk_energy), self.precision),
                "Structural_Energy": round(float(structural_energy), self.precision),
                "Directional_Share": round(float(directional_share), self.precision),
                "Directional_Breadth": round(float(directional_breadth), self.precision),
                "Directional_Balance": round(float(directional_balance), self.precision),
                "Directional_Reach": round(float(directional_reach), self.precision),
                "Purity": round(float(purity), self.precision),
                "Cohesion": round(float(cohesion), self.precision),
                "Participation_Rate": round(float(participation_rate), self.precision),
                "Effective_Breadth": round(float(effective_breadth), self.precision),
                "Effective_Size": round(float(effective_size), self.precision),
                "Signal_Quality": round(float(signal_quality), self.precision),
                "Size_Confidence": round(float(size_confidence), self.precision),
                "Dominant_Z": round(float(abs(dominant_z)), self.precision),
            },
        }

    def _rank_groups(self, groups: Dict[str, Any]) -> List[Tuple[str, Any]]:
        """
        [ACTION]
        Sorts groups by their calculated Energy.

        - **Orders:** Descending order of 'Energy' key.
        - **Returns:** List of (Group Name, Data Dict) tuples.
        """
        items = list(groups.items())
        items.sort(
            key=lambda kv: (
                float(kv[1].get("metrics", {}).get("Opportunity_Score", 0.0))
                if isinstance(kv[1], dict)
                else 0.0,
                float(kv[1].get("Energy", 0.0)) if isinstance(kv[1], dict) else 0.0,
            ),
            reverse=True,
        )
        return items

    def _finite_float(self, value: Any, default: float = 0.0) -> float:
        if isinstance(value, (int, float)) and np.isfinite(float(value)):
            return float(value)
        return float(default)

    def _confidence_label(self, metrics: Mapping[str, Any]) -> str:
        signal_quality = self._finite_float(metrics.get("Signal_Quality"))
        size_confidence = self._finite_float(metrics.get("Size_Confidence"))
        if signal_quality >= 0.66 and size_confidence >= 0.5:
            return "HIGH"
        if signal_quality >= 0.33:
            return "MEDIUM"
        return "LOW"

    def _direction_from_polarity(self, value: Any) -> str:
        polarity = self._finite_float(value)
        if abs(polarity) < 0.001:
            return "ABSTAIN"
        return "UP" if polarity > 0.0 else "DOWN"

    def _event_probability(self, payload: Mapping[str, Any]) -> float:
        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), Mapping) else {}
        if self._direction_from_polarity(payload.get("Polarity")) == "ABSTAIN":
            return 0.5
        signal_quality = self._finite_float(metrics.get("Signal_Quality") if isinstance(metrics, Mapping) else None)
        concentration = self._finite_float(payload.get("Directional_Concentration"))
        size_confidence = self._finite_float(metrics.get("Size_Confidence") if isinstance(metrics, Mapping) else None)
        strength = self._clip01(self._safe_sqrt(signal_quality * concentration) * (0.5 + 0.5 * size_confidence))
        return round(0.5 + (0.35 * strength), self.precision)

    def _artifact_ref(self, node_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        quality = metadata.get("quality") if isinstance(metadata.get("quality"), Mapping) else {}
        return {
            "artifact_id": node_id,
            "as_of": metadata.get("as_of"),
            "status": metadata.get("status") or payload.get("status"),
            "quality_tone": quality.get("tone", "unknown") if isinstance(quality, Mapping) else "unknown",
            "quality_reasons": list(quality.get("reasons", [])) if isinstance(quality.get("reasons"), list) else [],
        }

    def _source_artifact_refs(
        self,
        stock_payload: Mapping[str, Any],
        macro_payload: Mapping[str, Any],
        etf_payload: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        refs = [
            self._artifact_ref("global_stock_feed", stock_payload),
            self._artifact_ref("global_macro_feed", macro_payload),
        ]
        if etf_payload:
            refs.append(self._artifact_ref("global_etf_feed", etf_payload))
        return refs

    def _metric_attribution(self, payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
        raw = payload.get("metrics_raw") if isinstance(payload.get("metrics_raw"), Mapping) else {}
        norm = payload.get("metrics_norm") if isinstance(payload.get("metrics_norm"), Mapping) else {}
        rows: List[Dict[str, Any]] = []
        for key, normalized_value in norm.items() if isinstance(norm, Mapping) else []:
            if not isinstance(normalized_value, (int, float)):
                continue
            weight = self._metric_weight(str(key))
            weighted_value = float(normalized_value) * weight
            raw_value = raw.get(key) if isinstance(raw, Mapping) else None
            rows.append(
                {
                    "metric": str(key),
                    "bucket": self._metric_bucket(str(key)),
                    "raw": raw_value if isinstance(raw_value, (int, float, str)) else None,
                    "normalized": round(float(normalized_value), self.precision),
                    "weight": round(weight, self.precision),
                    "weighted_value": round(weighted_value, self.precision),
                    "abs_weighted_value": round(abs(weighted_value), self.precision),
                    "description": self.metric_descriptions.get(self._metric_semantic_key(str(key))),
                }
            )
        rows.sort(key=lambda item: float(item["abs_weighted_value"]), reverse=True)
        return rows

    def _explain_group(
        self,
        lane: str,
        group_name: str,
        payload: Mapping[str, Any],
        *,
        rank: int,
        source_artifact_refs: List[Dict[str, Any]],
        total_nan_before_imputation: int,
    ) -> Dict[str, Any]:
        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), Mapping) else {}
        metric_attribution = self._metric_attribution(payload)
        top_metric = metric_attribution[0] if metric_attribution else None
        return {
            "schema_version": "calculator_group_explain_v0",
            "lane": lane,
            "group": group_name,
            "rank": rank,
            "direction": self._direction_from_polarity(payload.get("Polarity")),
            "dominant_signal": payload.get("Dominant_Signal"),
            "score_components": {
                "Opportunity_Score": self._finite_float(metrics.get("Opportunity_Score") if isinstance(metrics, Mapping) else None),
                "Thrust_Score": self._finite_float(metrics.get("Thrust_Score") if isinstance(metrics, Mapping) else None),
                "Purity": self._finite_float(metrics.get("Purity") if isinstance(metrics, Mapping) else None),
                "Signal_Quality": self._finite_float(metrics.get("Signal_Quality") if isinstance(metrics, Mapping) else None),
                "Size_Confidence": self._finite_float(metrics.get("Size_Confidence") if isinstance(metrics, Mapping) else None),
                "Energy": self._finite_float(payload.get("Energy")),
                "Polarity": self._finite_float(payload.get("Polarity")),
                "Directional_Concentration": self._finite_float(payload.get("Directional_Concentration")),
            },
            "metric_attribution": metric_attribution,
            "member_attribution": {
                "members": list(payload.get("members", [])) if isinstance(payload.get("members"), list) else [],
                "size": int(payload.get("Size", 0) or 0),
                "cohesion": self._finite_float(metrics.get("Cohesion") if isinstance(metrics, Mapping) else None),
                "participation_rate": self._finite_float(metrics.get("Participation_Rate") if isinstance(metrics, Mapping) else None),
                "effective_breadth": self._finite_float(metrics.get("Effective_Breadth") if isinstance(metrics, Mapping) else None),
                "effective_size": self._finite_float(metrics.get("Effective_Size") if isinstance(metrics, Mapping) else None),
            },
            "data_quality_refs": {
                "source_artifacts": source_artifact_refs,
                "imputation_policy": self.imputation_policy,
                "total_nan_before_imputation": int(total_nan_before_imputation),
            },
            "deterministic_summary": (
                f"{lane}:{group_name} ranks {rank} by Opportunity_Score; "
                f"direction={self._direction_from_polarity(payload.get('Polarity'))}; "
                f"dominant_signal={payload.get('Dominant_Signal')}; "
                f"top_metric={top_metric.get('metric') if isinstance(top_metric, dict) else 'None'}."
            ),
        }

    def _build_explain_payload(
        self,
        ranked_by_lane: Dict[str, List[Tuple[str, Any]]],
        *,
        source_artifact_refs: List[Dict[str, Any]],
        total_nan_before_imputation: int,
    ) -> Dict[str, Any]:
        lanes: Dict[str, Dict[str, Any]] = {}
        for lane, ranked_groups in ranked_by_lane.items():
            lanes[lane] = {}
            for rank, (group_name, payload) in enumerate(ranked_groups, start=1):
                if not isinstance(payload, Mapping):
                    continue
                lanes[lane][group_name] = self._explain_group(
                    lane,
                    group_name,
                    payload,
                    rank=rank,
                    source_artifact_refs=source_artifact_refs,
                    total_nan_before_imputation=total_nan_before_imputation,
                )
        return {
            "schema_version": EXPLAIN_PAYLOAD_SCHEMA_VERSION,
            "run_id": self.run_id,
            "as_of": self.as_of,
            "method": "deterministic_metric_weight_attribution_plus_member_geometry",
            "lanes": lanes,
        }

    def _forecast_id(self, lane: str, group_name: str, horizon: str) -> str:
        token = "|".join([self.run_id, self.as_of, lane, group_name, horizon, DATA_SCHEMA_VERSION])
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        return f"calc_fc_{digest}"

    def _build_candidate_forecast_cards(
        self,
        ranked_by_lane: Dict[str, List[Tuple[str, Any]]],
        *,
        source_artifact_refs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        cards: List[Dict[str, Any]] = []
        per_horizon_budget = max(0, int(self.forecast_card_count))
        for lane, ranked_groups in ranked_by_lane.items():
            emitted_for_lane = 0
            for rank, (group_name, payload) in enumerate(ranked_groups, start=1):
                if emitted_for_lane >= per_horizon_budget or not isinstance(payload, Mapping):
                    break
                metrics = payload.get("metrics") if isinstance(payload.get("metrics"), Mapping) else {}
                direction = self._direction_from_polarity(payload.get("Polarity"))
                event_probability = self._event_probability(payload)
                confidence = self._confidence_label(metrics if isinstance(metrics, Mapping) else {})
                for horizon in self.forecast_card_horizons:
                    cards.append(
                        {
                            "schema_version": FORECAST_CARD_SCHEMA_VERSION,
                            "identity": {
                                "forecast_id": self._forecast_id(lane, group_name, horizon),
                                "run_id": self.run_id,
                                "generator_variant_id": f"{TOOL_NAME}:{DATA_SCHEMA_VERSION}:default",
                                "source_artifact_refs": source_artifact_refs,
                                "as_of": self.as_of,
                            },
                            "target": {
                                "universe": lane,
                                "entity_or_group": group_name,
                                "members": list(payload.get("members", [])) if isinstance(payload.get("members"), list) else [],
                                "horizon": horizon,
                                "event_definition": "group_directional_continuation_relative_to_configured_benchmark",
                                "benchmark_definition": "not_bound_until_cp1_commitment",
                                "direction": direction,
                            },
                            "belief": {
                                "kind": "calculator_score_proxy_not_calibrated",
                                "event_probability": event_probability,
                                "confidence": confidence,
                                "interval_or_quantiles": None,
                                "abstention_reason_if_any": "near_zero_polarity" if direction == "ABSTAIN" else None,
                            },
                            "explanation": {
                                "explain_ref": f"data.explain_payload.lanes.{lane}.{group_name}",
                                "dominant_signal": payload.get("Dominant_Signal"),
                                "metric_attribution": self._metric_attribution(payload)[:5],
                                "member_attribution": {
                                    "size": int(payload.get("Size", 0) or 0),
                                    "members": list(payload.get("members", [])) if isinstance(payload.get("members"), list) else [],
                                },
                                "macro_context_refs": [],
                                "data_quality_refs": source_artifact_refs,
                            },
                            "admissibility": {
                                "candidate_only_not_cp1_commitment": True,
                                "no_trade_advice_flag": True,
                                "leakage_guard": "subject_time_only_calculator_inputs",
                                "subject_truth_split_ref": "codex/substrate/contracts/schema_cp2.json::oracle_contract_model",
                                "cp1_prompt_or_policy_ref": "codex/substrate/contracts/schema_cp1.json",
                            },
                        }
                    )
                emitted_for_lane += 1
        return cards

    def execute(self) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Orchestrate the full cross-lane calculation pipeline from feed loading to ranked group output.
        - Guarantee: Returns a structured Success Envelope dict with metadata and data; any internal exception is caught and returned as a Failure Envelope.
        - Fails: None — all exceptions are captured into a failure envelope.
        - When-needed: Open when you need the exact calculator execution path that validates feed `as_of` alignment and turns normalized lane matrices into ranked cluster output.
        - Escalates-to: tools/macro/macro.py::run; tools/oracle/subject_index.py::run
        """
        try:
            # 1. Load Inputs
            stock_payload = self._load_json_artifact(self.stock_path) or {}
            macro_payload = self._load_json_artifact(self.macro_path) or {}
            etf_payload = self._load_json_artifact(self.etf_path) or {}

            stock_as_of = stock_payload.get("metadata", {}).get("as_of")
            macro_as_of = macro_payload.get("metadata", {}).get("as_of")
            if stock_as_of != self.as_of:
                raise LogicalFailure(
                    f"stock metadata.as_of mismatch: expected {self.as_of}, got {stock_as_of!r}"
                )
            if macro_as_of != self.as_of:
                raise LogicalFailure(
                    f"macro metadata.as_of mismatch: expected {self.as_of}, got {macro_as_of!r}"
                )
            # ETF as_of check: enforce if ETF payload was loaded, skip if absent
            if etf_payload:
                etf_as_of = etf_payload.get("metadata", {}).get("as_of")
                if etf_as_of != self.as_of:
                    raise LogicalFailure(
                        f"etf metadata.as_of mismatch: expected {self.as_of}, got {etf_as_of!r}"
                    )

            # 2. Parse DataFrames
            stock_df = self._parse_matrix(stock_payload, "stock")
            macro_df = self._parse_matrix(macro_payload, "macro")
            etf_df = self._parse_matrix(etf_payload, "etf") if etf_payload else pd.DataFrame()

            # 3. Compute Metrics (each lane normalized independently)
            stock_groups, stock_nan_count = self._compute_group_metrics(
                stock_df, self.group_col_stock, self.metrics_stock
            )
            macro_groups, macro_nan_count = self._compute_group_metrics(
                macro_df, self.group_col_macro, self.metrics_macro
            )
            etf_groups, etf_nan_count = self._compute_group_metrics(
                etf_df, self.group_col_etf, self.metrics_etf
            )
            total_nan_before_imputation = stock_nan_count + macro_nan_count + etf_nan_count

            # 4. Rank
            ranked_stock = self._rank_groups(stock_groups)
            ranked_macro = self._rank_groups(macro_groups)
            ranked_etf = self._rank_groups(etf_groups)

            # 5. Truncation
            if self.top_n and self.top_n > 0:
                ranked_stock = ranked_stock[:int(self.top_n)]
                ranked_macro = ranked_macro[:int(self.top_n)]
                ranked_etf = ranked_etf[:int(self.top_n)]

            ranked_by_lane = {
                "stock": ranked_stock,
                "macro": ranked_macro,
                "etf": ranked_etf,
            }
            source_artifact_refs = self._source_artifact_refs(stock_payload, macro_payload, etf_payload)
            explain_payload = self._build_explain_payload(
                ranked_by_lane,
                source_artifact_refs=source_artifact_refs,
                total_nan_before_imputation=total_nan_before_imputation,
            )
            candidate_forecast_cards = self._build_candidate_forecast_cards(
                ranked_by_lane,
                source_artifact_refs=source_artifact_refs,
            )

            # 6. Construct Output (Pure Return - Engine Saves)
            input_rows = int(len(stock_df) + len(macro_df) + len(etf_df))
            output_rows = int(len(ranked_stock) + len(ranked_macro) + len(ranked_etf))
            now = feed_envelope.utc_now()
            diag = feed_envelope.new_diagnostics(
                input_rows=input_rows,
                output_rows=output_rows,
                dropped_rows=0,
                imputed_nan_count=total_nan_before_imputation,
                imputed_metric_use_count=total_nan_before_imputation,
                dropped_row_count=0,
                imputation_policy=self.imputation_policy,
                normalization_policy=self.normalization_policy,
                signal_profile_method="empirical_shrinkage_plus_member_geometry",
                rank_metric="Opportunity_Score",
                candidate_forecast_card_count=len(candidate_forecast_cards),
                diagnostic_units={
                    "dropped_rows": "source rows removed before output",
                    "imputed_nan_count": "metric input uses imputed before aggregation",
                    "imputed_metric_use_count": "metric input uses imputed before aggregation",
                },
            )
            meta = feed_envelope.build_metadata(
                tool=TOOL_NAME,
                status="success",
                now=now,
                run_id=self.run_id,
                as_of=self.as_of,
                items_count=output_rows,
                diagnostics=diag,
                data_schema_version=DATA_SCHEMA_VERSION,
                timestamp=now.iso,
                legend=LEGEND,
                extra={
                    "metric_semantics": self._metric_semantics_payload(),
                    "forecast_card_schema_version": FORECAST_CARD_SCHEMA_VERSION,
                    "explain_payload_schema_version": EXPLAIN_PAYLOAD_SCHEMA_VERSION,
                },
            )
            return {
                "metadata": meta,
                "data": {
                    "stock": ranked_stock,
                    "macro": ranked_macro,
                    "etf": ranked_etf,
                    "explain_payload": explain_payload,
                    "candidate_forecast_cards": candidate_forecast_cards,
                },
            }

        except Exception as e:
            logger.exception("Calculator execution failed")
            return self._create_failure_envelope(str(e))

    def _create_failure_envelope(self, error: str) -> Dict[str, Any]:
        """
        [ACTION]
        Constructs a standardized failure response.

        - **Returns:** Dictionary with status="failure", error details, and empty data.
        """
        now = feed_envelope.utc_now()
        diag = feed_envelope.new_diagnostics()
        if error:
            feed_envelope.append_warning(diag, error)
        meta = feed_envelope.build_metadata(
            tool=TOOL_NAME,
            status="failure",
            now=now,
            run_id=self.run_id,
            as_of=self.as_of,
            items_count=0,
            diagnostics=diag,
            data_schema_version=DATA_SCHEMA_VERSION,
            timestamp=now.iso,
            legend=LEGEND,
            error=error,
        )
        return {"metadata": meta, "data": {}}


def run(config: Dict[str, Any], run_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Provide the tool-harness entrypoint that instantiates StandardActor and returns a Success or Failure envelope.
    - Guarantee: Returns a dict with metadata and data keys in either Success or Failure envelope shape for every input.
    - Fails: None — harness-level exceptions are caught and returned as a Failure envelope.
    - When-needed: Open when the tool harness or a downstream market-intelligence lane needs the calculator entrypoint and its failure-envelope behavior.
    - Escalates-to: tools/oracle/subject_index.py::run
    """
    # [FIX] Ensure run_dir is a Path object, even if Engine passes a string.
    run_dir = Path(run_dir) if run_dir else Path(".")

    try:
        actor = StandardActor(config, run_dir)
        return actor.execute()
    except Exception as e:
        logger.exception("Calculator harness failed")
        now = feed_envelope.utc_now()
        diag = feed_envelope.new_diagnostics()
        if str(e):
            feed_envelope.append_warning(diag, str(e))
        # Harness-level failure: actor did not build, so run_id / as_of fall back
        # to whatever the caller supplied via run_dir (matches pre-migration behavior
        # where run_id was absent from the harness-level envelope).
        run_id = feed_envelope.resolve_run_id(None, run_dir)
        meta = feed_envelope.build_metadata(
            tool=TOOL_NAME,
            status="failure",
            now=now,
            run_id=run_id,
            as_of=now.iso,
            items_count=0,
            diagnostics=diag,
            data_schema_version=DATA_SCHEMA_VERSION,
            timestamp=now.iso,
            error=str(e),
        )
        # Pre-migration harness-level envelope did NOT include run_id / as_of; drop
        # them here to preserve bit-shape. Any future caller that needs them can
        # read from the inner execute() envelope.
        meta.pop("run_id", None)
        meta.pop("as_of", None)
        return {"metadata": meta, "data": {}}
