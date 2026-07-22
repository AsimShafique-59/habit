import { BarChart3 } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Analytics"
      description="Streaks, heatmaps, correlations, and progress reports."
      icon={BarChart3}
    />
  );
}
