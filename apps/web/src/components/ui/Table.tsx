import type { ReactNode } from "react";

export function Table({
  headers,
  children,
  caption,
  className = "",
}: {
  headers: string[];
  children: ReactNode;
  caption?: string;
  className?: string;
}) {
  return (
    <div className={`overflow-x-auto rounded-[var(--radius-md,10px)] border border-[var(--border)] bg-[var(--card,#111520)] ${className}`}>
      <table className="w-full min-w-[20rem] border-collapse text-left text-sm">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        <thead>
          <tr className="border-b border-[var(--border)] bg-[var(--surface-2,#181e2e)]/50 font-mono text-[11px] uppercase tracking-wider text-[var(--muted-foreground)]">
            {headers.map((h) => (
              <th key={h} scope="col" className="px-4 py-3 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">{children}</tbody>
      </table>
    </div>
  );
}

export function Tr({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <tr className={`transition-colors hover:bg-[var(--surface-2,#181e2e)]/40 ${className}`}>
      {children}
    </tr>
  );
}

export function Td({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <td className={`px-4 py-3 align-middle text-[var(--fg)] ${className}`}>{children}</td>;
}
