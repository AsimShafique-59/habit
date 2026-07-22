import { Sparkles } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Motivation"
      description="Structured quit/change programs with daily check-ins."
      icon={Sparkles}
    />
  );
}
