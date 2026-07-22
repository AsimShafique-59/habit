import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowLeft, Hammer } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type ComingSoonProps = {
  title: string;
  description: string;
  icon: LucideIcon;
};

export function ComingSoon({ title, description, icon: Icon }: ComingSoonProps) {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <Card className="w-full max-w-md border-dashed">
        <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
            <Icon className="h-8 w-8 text-muted-foreground" />
            <span className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <Hammer className="h-3.5 w-3.5" />
            </span>
          </div>

          <Badge variant="secondary" className="uppercase tracking-wide">
            Coming soon
          </Badge>

          <div className="space-y-1.5">
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>

          <Link
            href="/dashboard"
            className={cn(buttonVariants({ variant: "outline", size: "sm" }), "mt-2")}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to dashboard
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
