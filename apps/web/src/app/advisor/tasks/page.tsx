"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/Skeleton";

const TasksWorkspace = dynamic(
  () => import("@/components/advisor/AdvisorWorkspace").then((m) => m.TasksWorkspace),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,
  },
);

export default function AdvisorTasksPage() {
  return <TasksWorkspace />;
}
