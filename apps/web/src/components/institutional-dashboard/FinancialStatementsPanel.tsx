import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ds";
import type {
  FinancialStatementsView,
  StatementLine,
} from "@/lib/institutional-dashboard/types";

function LineGrid({ lines }: { lines: StatementLine[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {lines.map((line) => (
        <MetricCell key={line.label} label={line.label} field={line.field} />
      ))}
    </div>
  );
}

const TAB_ITEMS = [
  { id: "income", label: "Income Statement", key: "incomeStatement" as const },
  { id: "balance", label: "Balance Sheet", key: "balanceSheet" as const },
  { id: "cash", label: "Cash Flow", key: "cashFlow" as const },
  { id: "trends", label: "Historical Trends", key: "historicalTrends" as const },
  { id: "growth", label: "Growth", key: "growthRates" as const },
  { id: "margins", label: "Margins", key: "margins" as const },
  {
    id: "capital",
    label: "Capital Allocation",
    key: "capitalAllocation" as const,
  },
  { id: "ratios", label: "Financial Ratios", key: "ratios" as const },
] as const;

export function FinancialStatementsPanel({
  view,
}: {
  view: FinancialStatementsView;
}) {
  return (
    <SectionShell
      id="rs-003-financial"
      title="Financial Statement Analysis"
      description="RS-003 — user-submitted statement inputs; derived ratios only when calculated by engines"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <MetricCell label="Reporting period" field={view.reportingPeriod} />
        <MetricCell label="Source" field={view.source} />
      </div>
      <Tabs defaultValue="income" className="w-full">
        <TabsList
          aria-label="Financial statement views"
          className="flex h-auto min-h-11 w-full flex-wrap justify-start"
        >
          {TAB_ITEMS.map((item) => (
            <TabsTrigger key={item.id} value={item.id} className="min-h-9">
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {TAB_ITEMS.map((item) => (
          <TabsContent key={item.id} value={item.id}>
            <LineGrid lines={view[item.key]} />
          </TabsContent>
        ))}
      </Tabs>
    </SectionShell>
  );
}
