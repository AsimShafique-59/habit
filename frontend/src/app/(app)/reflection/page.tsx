import { BookOpen } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Reflection"
      description="Journal entries, mood tracking, and daily prompts."
      icon={BookOpen}
    />
  );
}
