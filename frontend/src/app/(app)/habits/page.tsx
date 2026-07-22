import { ListChecks } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Habits"
      description="Create, track, and complete your daily and weekly habits."
      icon={ListChecks}
    />
  );
}
