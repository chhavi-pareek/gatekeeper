"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toaster";
import { api } from "@/lib/api";
import { 
  Code, 
  Activity, 
  Shield, 
  TrendingUp,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw
} from "lucide-react";

interface OverviewData {
  total_services: number;
  requests_today: number;
  top_services: Array<{
    name: string;
    request_count: number;
  }>;
  average_rate_limit_usage: number;
  gateway_status: string;
}

export default function Home() {
  const [overviewData, setOverviewData] = useState<OverviewData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.getOverview();
      setOverviewData(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load overview data";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-semibold tracking-tight">Overview</h1>
            <p className="text-muted-foreground text-sm">
              Monitor your gateway services and API usage
            </p>
          </div>
          {!isLoading && (
            <button
              onClick={fetchOverviewData}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-muted"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          )}
        </div>

        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Statistics Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Total APIs Registered */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total APIs
              </CardTitle>
              <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center">
                <Code className="h-4 w-4 text-primary" />
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <>
                  <div className="text-2xl font-semibold tracking-tight">
                    {overviewData?.total_services || 0}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Registered services
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          {/* Total Requests Today */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Requests Today
              </CardTitle>
              <div className="h-8 w-8 rounded-md bg-blue-500/10 flex items-center justify-center">
                <Activity className="h-4 w-4 text-blue-500" />
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <>
                  <div className="text-2xl font-semibold tracking-tight">
                    {overviewData?.requests_today.toLocaleString() || 0}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Total requests processed
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          {/* Rate Limit Status */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Rate Limit
              </CardTitle>
              <div className="h-8 w-8 rounded-md bg-amber-500/10 flex items-center justify-center">
                <Shield className="h-4 w-4 text-amber-500" />
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-20" />
                  <Skeleton className="h-1.5 w-full" />
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <div className="flex items-baseline gap-2">
                      <div className="text-2xl font-semibold tracking-tight">
                        {overviewData?.average_rate_limit_usage.toFixed(1) || 0}%
                      </div>
                      <Badge 
                        variant={
                          (overviewData?.average_rate_limit_usage || 0) > 80 
                            ? "destructive" 
                            : (overviewData?.average_rate_limit_usage || 0) > 60 
                            ? "default" 
                            : "secondary"
                        }
                        className="text-xs"
                      >
                        {(overviewData?.average_rate_limit_usage || 0) > 80 
                          ? "high" 
                          : (overviewData?.average_rate_limit_usage || 0) > 60 
                          ? "moderate" 
                          : "healthy"}
                      </Badge>
                    </div>
                    <div className="w-full bg-muted rounded-full h-1.5">
                      <div 
                        className={`h-1.5 rounded-full transition-all ${
                          (overviewData?.average_rate_limit_usage || 0) > 80 
                            ? 'bg-red-500' 
                            : (overviewData?.average_rate_limit_usage || 0) > 60 
                            ? 'bg-amber-500' 
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(overviewData?.average_rate_limit_usage || 0, 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Average usage across all APIs
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Gateway Health */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Gateway Health
              </CardTitle>
              <div className="h-8 w-8 rounded-md bg-green-500/10 flex items-center justify-center">
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                ) : overviewData?.gateway_status?.toLowerCase() === "operational" ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-500" />
                )}
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <div className="text-2xl font-semibold tracking-tight capitalize">
                      {overviewData?.gateway_status || "Unknown"}
                    </div>
                    <div className="flex items-center gap-1">
                      <div className={`h-2 w-2 rounded-full ${
                        overviewData?.gateway_status?.toLowerCase() === "operational"
                          ? 'bg-green-500 animate-pulse' 
                          : 'bg-red-500'
                      }`} />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {overviewData?.gateway_status?.toLowerCase() === "operational"
                      ? "All systems operational"
                      : "Service unavailable"}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Additional Metrics Section */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Request Trends */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-base font-semibold">Request Trends</CardTitle>
              <CardDescription className="text-xs">
                Last 7 days
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center h-32 text-muted-foreground">
                <div className="text-center space-y-2">
                  <TrendingUp className="h-8 w-8 mx-auto opacity-50" />
                  <p className="text-xs">Chart visualization coming soon</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Top APIs */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-base font-semibold">Top APIs</CardTitle>
              <CardDescription className="text-xs">
                Most requested services
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : overviewData && overviewData.top_services && overviewData.top_services.length > 0 ? (
                <div className="space-y-3">
                  {overviewData.top_services.map((service) => (
                    <div key={service.name} className="flex items-center justify-between p-2 rounded-md hover:bg-muted/50 transition-colors">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-primary" />
                        <span className="text-sm font-medium">{service.name}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {service.request_count.toLocaleString()} requests
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-32 text-muted-foreground">
                  <div className="text-center space-y-2">
                    <Activity className="h-8 w-8 mx-auto opacity-50" />
                    <p className="text-xs">No service data available</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
    </div>
    </DashboardLayout>
  );
}
