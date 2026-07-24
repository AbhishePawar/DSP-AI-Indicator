"use client";

import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { useTheme, type ThemeMode } from "@/providers/ThemeProvider";

const MODES: ThemeMode[] = ["light", "dark", "system"];

export default function SettingsPage() {
  const { mode, resolved, setMode } = useTheme();

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Client preferences only. Theme mode is stored locally; business logic stays on the API."
      />
      <Card>
        <CardHeader title="Appearance" description={`Resolved: ${resolved}`} />
        <CardBody className="flex flex-wrap gap-2">
          {MODES.map((m) => (
            <Button
              key={m}
              variant={mode === m ? "primary" : "secondary"}
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
            >
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </Button>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
