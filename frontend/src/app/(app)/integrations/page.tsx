import { Cable } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Integrations"
      description="Connect Apple Health, Google Fit, and calendar sync."
      icon={Cable}
    />
  );
}
