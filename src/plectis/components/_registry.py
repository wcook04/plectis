"""Reviewed component slug to generated Dafny module bindings.

This allowlist is source code, not a user-supplied plugin registry. Each entry
must also have matching reviewed source inventory and manifest pins in
``plectis._sealed_kernel`` and its formal metadata.
"""

KERNELS: dict[str, str] = {
    "budget_packing": "BudgetPacking",
    "dependency_reachability": "DependencyReachability",
    "egress_policy": "EgressPolicy",
    "evidence_diff": "EvidenceDiff",
    "information_flow": "InformationFlow",
    "mcp_authority": "McpAuthority",
    "navigation_metrics": "NavigationMetrics",
    "ownership_classification": "OwnershipClassification",
    "premise_ranking": "PremiseRanking",
    "sandbox_policy": "SandboxPolicy",
    "tactic_selection": "TacticSelection",
    "walkthrough_validation": "WalkthroughValidation",
}
