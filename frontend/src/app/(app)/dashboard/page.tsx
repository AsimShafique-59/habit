import { LayoutDashboard } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Dashboard"
      description="Your daily snapshot — streaks, momentum, and today's habits."
      icon={LayoutDashboard}
    />
  );
}
