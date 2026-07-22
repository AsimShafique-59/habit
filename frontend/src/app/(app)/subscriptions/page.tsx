"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, CreditCard, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import {
  cancelSubscription,
  getMySubscription,
  listSubscriptionPlans,
  type SubscriptionPlan,
  type UserSubscription,
} from "@/lib/api/subscriptions";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function SubscriptionsPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [plansRes, subRes] = await Promise.all([listSubscriptionPlans(), getMySubscription()]);
      setPlans(plansRes);
      setSubscription(subRes);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not load subscription.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCancel() {
    setCancelling(true);
    try {
      const updated = await cancelSubscription();
      setSubscription(updated);
      toast.success("Subscription cancelled.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Could not cancel subscription.";
      toast.error(message);
    } finally {
      setCancelling(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 p-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Subscription</h1>
        <p className="text-sm text-muted-foreground">Plan catalog and current billing status.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <ShieldCheck className="h-4 w-4" />
            Current Plan
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          {loading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <>
              <div>
                <p className="text-2xl font-semibold tracking-tight">{subscription?.tier ?? "free"}</p>
                <p className="text-sm text-muted-foreground">
                  {subscription?.status ?? "pending"} via {subscription?.provider ?? "manual"}
                </p>
              </div>
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={cancelling || !subscription || subscription.status !== "active"}
              >
                {cancelling ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}
                Cancel
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {loading ? (
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-64 w-full" />)
        ) : plans.length === 0 ? (
          <Card>
            <CardContent className="py-14 text-center text-sm text-muted-foreground">No plans are active.</CardContent>
          </Card>
        ) : (
          plans.map((plan) => (
            <Card key={plan.id} className={plan.is_featured ? "border-primary" : ""}>
              <CardHeader>
                <CardTitle className="flex items-start justify-between gap-3 text-base">
                  {plan.name}
                  {plan.is_featured ? <Badge>Featured</Badge> : null}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-3xl font-semibold tracking-tight">${plan.price_usd}</p>
                  <p className="text-sm text-muted-foreground">{plan.duration_days} days</p>
                </div>
                <p className="text-sm text-muted-foreground">{plan.description}</p>
                <div className="space-y-2">
                  {plan.features.map((feature) => (
                    <div key={feature} className="flex items-center gap-2 text-sm">
                      <Check className="h-4 w-4 text-primary" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
