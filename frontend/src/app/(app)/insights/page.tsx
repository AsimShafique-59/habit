import { Headphones } from "lucide-react";

import { ComingSoon } from "@/components/coming-soon";

export default function Page() {
  return (
    <ComingSoon
      title="Insights"
      description="Guided audio sessions to build focus and motivation."
      icon={Headphones}
    />
  );
}
