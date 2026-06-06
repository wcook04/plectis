// [PURPOSE] Pure summarization helpers extracted from Annexes.tsx so the .tsx
// only exports the React component (react-refresh/only-export-components).
import type { LibraryAnnexSummary } from '../api';

const ANNEX_SOURCE_KIND_ORDER = ['git_repo', 'document', 'unknown'] as const;
const ANNEX_SOURCE_KIND_ORDER_SET = new Set<string>(ANNEX_SOURCE_KIND_ORDER);

export type AnnexesSummary = {
  total: number;
  totalNotes: number;
  noteBearing: number;
  sourceKinds: Array<[string, number]>;
  domains: Array<[string, number]>;
  problemSpaces: Array<[string, number]>;
};

function countValues(
  annexes: LibraryAnnexSummary[],
  readValues: (annex: LibraryAnnexSummary) => string[],
): Array<[string, number]> {
  const counts = new Map<string, number>();
  for (const annex of annexes) {
    for (const value of readValues(annex)) {
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
  }
  return Array.from(counts.entries()).sort((left, right) => right[1] - left[1]);
}

export function summarizeAnnexes(annexes: LibraryAnnexSummary[]): AnnexesSummary {
  return {
    total: annexes.length,
    totalNotes: annexes.reduce((sum, annex) => sum + annex.note_count, 0),
    noteBearing: annexes.filter((annex) => annex.note_count > 0).length,
    sourceKinds: countValues(annexes, (annex) => (annex.source_kind ? [annex.source_kind] : [])),
    domains: countValues(annexes, (annex) => annex.domains ?? []),
    problemSpaces: countValues(annexes, (annex) => annex.problem_spaces ?? []),
  };
}

export function annexSourceKindKey(kind: string | null | undefined): string {
  return kind?.trim() || 'unknown';
}

export function groupAnnexesBySourceKind(
  annexes: LibraryAnnexSummary[],
): Array<[string, LibraryAnnexSummary[]]> {
  const groups = new Map<string, LibraryAnnexSummary[]>();
  for (const annex of annexes) {
    const key = annexSourceKindKey(annex.source_kind);
    const bucket = groups.get(key);
    if (bucket) {
      bucket.push(annex);
      continue;
    }
    groups.set(key, [annex]);
  }

  const orderedKeys = [
    ...ANNEX_SOURCE_KIND_ORDER.filter((kind) => groups.has(kind)),
    ...Array.from(groups.keys())
      .filter((kind) => !ANNEX_SOURCE_KIND_ORDER_SET.has(kind))
      .sort((left, right) => left.localeCompare(right)),
  ];

  return orderedKeys.map((kind) => [kind, groups.get(kind) ?? []]);
}

export function describeAnnexSourceKindGroup(
  kind: string | null | undefined,
  groupCount: number,
  totalCount: number,
): {
  kicker: string;
  countText: string;
  ratioText: string;
} {
  const key = annexSourceKindKey(kind);
  const countText = `${groupCount} ${groupCount === 1 ? 'annex' : 'annexes'}`;
  const ratio = totalCount > 0 ? Math.round((groupCount / totalCount) * 100) : 0;

  switch (key) {
    case 'git_repo':
      return {
        kicker: 'repo-backed substrate',
        countText,
        ratioText: `${ratio}% of slice`,
      };
    case 'document':
      return {
        kicker: 'document-mined references',
        countText,
        ratioText: `${ratio}% of slice`,
      };
    case 'unknown':
      return {
        kicker: 'unclassified registry entries',
        countText,
        ratioText: `${ratio}% of slice`,
      };
    default:
      return {
        kicker: 'uncatalogued source kind',
        countText,
        ratioText: `${ratio}% of slice`,
      };
  }
}
