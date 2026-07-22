import { Bot } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="AI Coach"
      description="AI-generated habit suggestions and coaching reviews."
      icon={Bot}
    />
  );
}
