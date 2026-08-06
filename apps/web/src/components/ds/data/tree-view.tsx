"use client";

import * as React from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TreeNode {
  id: string;
  label: React.ReactNode;
  children?: TreeNode[];
}

export interface TreeViewProps {
  nodes: TreeNode[];
  className?: string;
  defaultExpandedIds?: string[];
  onSelect?: (id: string) => void;
  selectedId?: string;
}

function TreeNodeItem({
  node,
  depth,
  expanded,
  toggle,
  selectedId,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  expanded: Set<string>;
  toggle: (id: string) => void;
  selectedId?: string;
  onSelect?: (id: string) => void;
}) {
  const hasChildren = Boolean(node.children?.length);
  const isExpanded = expanded.has(node.id);
  const isSelected = selectedId === node.id;

  return (
    <li role="treeitem" aria-expanded={hasChildren ? isExpanded : undefined} aria-selected={isSelected}>
      <div
        className={cn(
          "flex items-center gap-1 rounded-[var(--radius-md,0.5rem)] py-1 pr-2 text-sm",
          isSelected && "bg-[var(--accent-soft)] text-[var(--accent)]",
        )}
        style={{ paddingLeft: `${depth * 0.75 + 0.25}rem` }}
      >
        {hasChildren ? (
          <button
            type="button"
            aria-label={isExpanded ? `Collapse ${String(node.label)}` : `Expand ${String(node.label)}`}
            className={cn(
              "inline-flex h-6 w-6 items-center justify-center rounded-sm text-[var(--muted)]",
              "hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
              "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
            )}
            onClick={() => toggle(node.id)}
          >
            <ChevronRight
              className={cn("h-4 w-4 transition-transform", isExpanded && "rotate-90")}
              aria-hidden
            />
          </button>
        ) : (
          <span className="inline-block h-6 w-6" aria-hidden />
        )}
        <button
          type="button"
          className={cn(
            "flex-1 truncate rounded-sm px-1 py-0.5 text-left",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
            "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
          )}
          onClick={() => onSelect?.(node.id)}
        >
          {node.label}
        </button>
      </div>
      {hasChildren && isExpanded ? (
        <ul role="group" className="m-0 list-none p-0">
          {node.children!.map((child) => (
            <TreeNodeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              toggle={toggle}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function TreeView({
  nodes,
  className,
  defaultExpandedIds = [],
  onSelect,
  selectedId,
}: TreeViewProps) {
  const [expanded, setExpanded] = React.useState<Set<string>>(
    () => new Set(defaultExpandedIds),
  );

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <ul
      role="tree"
      className={cn(
        "m-0 list-none rounded-[var(--radius-md,0.5rem)] border border-[var(--border)]",
        "bg-[var(--surface)] p-1 text-[var(--fg)]",
        className,
      )}
    >
      {nodes.map((node) => (
        <TreeNodeItem
          key={node.id}
          node={node}
          depth={0}
          expanded={expanded}
          toggle={toggle}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      ))}
    </ul>
  );
}

export { TreeView };
