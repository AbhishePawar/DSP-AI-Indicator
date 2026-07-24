import { SmartHeader } from "@/components/analysis/MarketIntelligenceSection";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { AiChallengeView, AssumptionItem } from "@/lib/analysis/types";

/** AI Challenge assumption chip — Sprint 4 explorer uses AssumptionCard.tsx */
export function ChallengeAssumptionCard({ item }: { item: AssumptionItem }) {
  return (
    <Card>
      <CardHeader title="Assumption" />
      <CardBody className="space-y-2 text-sm">
        <p className="font-medium">{item.statement}</p>
        <p className="text-[var(--muted)]">Importance: {item.importance}</p>
        <ValueCategoryBadge category={item.category} />
      </CardBody>
    </Card>
  );
}

export function ResearchGapCard({ gaps }: { gaps: string[] }) {
  return (
    <Card>
      <CardHeader title="Research gaps" />
      <CardBody>
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {gaps.map((g) => (
            <li key={g}>{g}</li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export function ChallengeCard({ challenge }: { challenge: AiChallengeView }) {
  return (
    <Card className="border-[var(--accent)]/30">
      <CardHeader
        title={`Challenging: ${challenge.conclusionLabel}`}
        action={<ConfidenceBadge level={challenge.confidence} />}
      />
      <CardBody className="space-y-4 text-sm">
        <div className="flex flex-wrap gap-2">
          <ValueCategoryBadge category={challenge.category} />
          <SourceBadge source={challenge.source} />
        </div>
        <ListBlock label="What evidence supports this?" items={challenge.supportingEvidence} />
        <ListBlock
          label="What evidence contradicts this?"
          items={challenge.contradictingEvidence}
        />
        <ListBlock
          label="What could invalidate this conclusion?"
          items={challenge.whatCouldInvalidate}
        />
        <ListBlock
          label="What would change our opinion?"
          items={challenge.whatWouldChangeOpinion}
        />
        <ListBlock label="Limitations" items={challenge.limitations} />
        <ListBlock label="Investor watchpoints" items={challenge.investorWatchpoints} />
      </CardBody>
    </Card>
  );
}

function ListBlock({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      {items.length ? (
        <ul className="mt-1 list-disc pl-5">
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-[var(--muted)]">Unavailable</p>
      )}
    </div>
  );
}

export function AiChallengeSection({ challenge }: { challenge: AiChallengeView }) {
  return (
    <div className="space-y-4">
      <SmartHeader
        title="AI Challenge Mode"
        changed="Structured challenge scaffold is active — full model challenge awaits Copilot."
        monitor="Pressure-test assumptions and research gaps before trusting any DSP View."
      />
      <ChallengeCard challenge={challenge} />
      <div className="grid gap-4 md:grid-cols-2">
        {challenge.assumptions.map((a) => (
          <ChallengeAssumptionCard key={a.id} item={a} />
        ))}
      </div>
      <ResearchGapCard gaps={challenge.researchGaps} />
    </div>
  );
}
