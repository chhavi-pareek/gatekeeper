"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toaster";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import {
  Fingerprint,
  Search,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Shield,
  Info
} from "lucide-react";

interface ServiceData {
  id: number;
  name: string;
  target_url: string;
  watermarking_enabled: boolean;
}

interface WatermarkResult {
  watermark_found: boolean;
  raw_watermark: string;
  decoded: {
    service_id: number;
    service_name: string;
    api_key_id: number;
    api_key_masked: string;
    request_id: string;
    timestamp: string;
  };
  attribution: string;
}

export default function DataProtectionPage() {
  const [services, setServices] = useState<ServiceData[]>([]);
  const [isLoadingServices, setIsLoadingServices] = useState(true);
  const [togglingServiceId, setTogglingServiceId] = useState<number | null>(null);
  const [verifyInput, setVerifyInput] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<WatermarkResult | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    setIsLoadingServices(true);
    try {
      const data = await api.listServices();
      setServices(data.services);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load services";
      toast.error(errorMessage);
    } finally {
      setIsLoadingServices(false);
    }
  };

  const handleToggleWatermarking = async (serviceId: number, currentEnabled: boolean) => {
    setTogglingServiceId(serviceId);
    try {
      const result = await api.toggleWatermarking(serviceId, !currentEnabled);
      toast.success(result.message);
      setServices((prev) =>
        prev.map((s) =>
          s.id === serviceId ? { ...s, watermarking_enabled: !currentEnabled } : s
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to toggle watermarking";
      toast.error(errorMessage);
    } finally {
      setTogglingServiceId(null);
    }
  };

  const handleVerifyWatermark = async () => {
    if (!verifyInput.trim()) {
      toast.error("Please paste some data to verify");
      return;
    }
    
    setIsVerifying(true);
    setVerifyResult(null);
    setVerifyError(null);
    
    try {
      const result = await api.verifyWatermark(verifyInput);
      setVerifyResult(result);
      toast.success("Watermark found and decoded!");
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Verification failed";
      setVerifyError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsVerifying(false);
    }
  };

  const clearVerification = () => {
    setVerifyInput("");
    setVerifyResult(null);
    setVerifyError(null);
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">Data Protection</h1>
          <p className="text-muted-foreground text-sm">
            Watermark API responses for leak attribution and tracing
          </p>
        </div>

        {/* How It Works */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Info className="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <CardTitle>How Watermarking Works</CardTitle>
                <CardDescription className="text-xs">
                  Invisible tracing for data leak attribution
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="border-purple-500/50 bg-purple-500/5">
              <Fingerprint className="h-4 w-4 text-purple-500" />
              <AlertDescription className="text-sm text-purple-600 dark:text-purple-400">
                <strong>Response Watermarking:</strong> When enabled, each API response is embedded with a unique, 
                traceable watermark containing the service ID, API key ID, request ID, and timestamp. 
                If data is leaked, you can trace it back to the source.
              </AlertDescription>
            </Alert>

            {/* Example Responses */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Without Watermark (JSON)</Label>
                <pre className="rounded-md border border-border/50 bg-muted/30 p-3 text-xs font-mono overflow-x-auto">
{`{
  "id": 1,
  "name": "Product A",
  "price": 29.99
}`}
                </pre>
              </div>
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">With Watermark (JSON)</Label>
                <pre className="rounded-md border border-purple-500/30 bg-purple-500/5 p-3 text-xs font-mono overflow-x-auto">
{`{
  "id": 1,
  "name": "Product A",
  "price": 29.99,
  "_gaas_watermark": "MXwyfGFiY2..."
}`}
                </pre>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Service Watermarking Toggle */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <Shield className="h-5 w-5 text-purple-500" />
                </div>
                <div>
                  <CardTitle>Service Watermarking</CardTitle>
                  <CardDescription className="text-xs">
                    Enable or disable watermarking per service
                  </CardDescription>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchServices}
                disabled={isLoadingServices}
              >
                <RefreshCw className={`h-4 w-4 ${isLoadingServices ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingServices ? (
              <div className="space-y-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : services.length === 0 ? (
              <div className="rounded-md border border-dashed border-border/50 p-8 text-center">
                <Fingerprint className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-sm font-medium mb-1">No services registered</p>
                <p className="text-xs text-muted-foreground">
                  Register an API first to enable watermarking.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {services.map((service) => (
                  <div
                    key={service.id}
                    className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4 hover:bg-muted/50 transition-colors"
                  >
                    <div className="space-y-1 flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium">{service.name}</p>
                        <Badge variant="outline" className="text-xs">
                          ID: {service.id}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {service.target_url}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 ml-4">
                      <Badge
                        variant={service.watermarking_enabled ? "default" : "secondary"}
                        className={service.watermarking_enabled ? "bg-purple-500/20 text-purple-500 border-purple-500/30" : ""}
                      >
                        {service.watermarking_enabled ? "Enabled" : "Disabled"}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleWatermarking(service.id, service.watermarking_enabled)}
                        disabled={togglingServiceId === service.id}
                        className="min-w-[100px]"
                      >
                        {togglingServiceId === service.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : service.watermarking_enabled ? (
                          <>
                            <ToggleRight className="h-4 w-4 mr-2 text-purple-500" />
                            Disable
                          </>
                        ) : (
                          <>
                            <ToggleLeft className="h-4 w-4 mr-2" />
                            Enable
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Verify Leaked Data */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <Search className="h-5 w-5 text-orange-500" />
              </div>
              <div>
                <CardTitle>Verify Leaked Data</CardTitle>
                <CardDescription className="text-xs">
                  Paste leaked response data to extract and decode the watermark
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              If you suspect data has been leaked, paste the response below. 
              We&apos;ll extract the watermark and reveal which API key accessed it and when.
            </p>
            
            <Textarea
              placeholder={`Paste leaked data here...\n\nExample:\n{"id": 1, "name": "Product", "_gaas_watermark": "MXwyfGFiY2..."}`}
              value={verifyInput}
              onChange={(e) => setVerifyInput(e.target.value)}
              className="min-h-[150px] font-mono text-xs"
            />
            
            <div className="flex gap-2">
              <Button
                onClick={handleVerifyWatermark}
                disabled={isVerifying || !verifyInput.trim()}
                className="flex-1"
              >
                {isVerifying ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Verify & Extract Watermark
                  </>
                )}
              </Button>
              {(verifyInput || verifyResult || verifyError) && (
                <Button variant="outline" onClick={clearVerification}>
                  Clear
                </Button>
              )}
            </div>

            {/* Verification Error */}
            {verifyError && (
              <Alert className="border-red-500/50 bg-red-500/5">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <AlertDescription className="text-sm text-red-600 dark:text-red-400">
                  {verifyError}
                </AlertDescription>
              </Alert>
            )}

            {/* Verification Results */}
            {verifyResult && (
              <div className="rounded-md border border-green-500/50 bg-green-500/5 p-4 space-y-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                  <span className="text-base font-medium text-green-600 dark:text-green-400">
                    Watermark Found & Decoded
                  </span>
                </div>
                
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-1 p-3 rounded-md bg-background/50">
                    <p className="text-xs text-muted-foreground">Service</p>
                    <p className="text-sm font-medium">
                      {verifyResult.decoded.service_name} 
                      <span className="text-muted-foreground ml-1">(ID: {verifyResult.decoded.service_id})</span>
                    </p>
                  </div>
                  <div className="space-y-1 p-3 rounded-md bg-background/50">
                    <p className="text-xs text-muted-foreground">API Key</p>
                    <p className="text-sm font-mono">
                      {verifyResult.decoded.api_key_masked}
                      <span className="text-muted-foreground ml-1">(ID: {verifyResult.decoded.api_key_id})</span>
                    </p>
                  </div>
                  <div className="space-y-1 p-3 rounded-md bg-background/50">
                    <p className="text-xs text-muted-foreground">Request ID</p>
                    <p className="text-sm font-mono">{verifyResult.decoded.request_id}</p>
                  </div>
                  <div className="space-y-1 p-3 rounded-md bg-background/50">
                    <p className="text-xs text-muted-foreground">Timestamp</p>
                    <p className="text-sm">{new Date(verifyResult.decoded.timestamp).toLocaleString()}</p>
                  </div>
                </div>

                <div className="rounded-md bg-muted/50 p-4 border border-border/50">
                  <p className="text-xs text-muted-foreground mb-2">Attribution Summary</p>
                  <p className="text-sm font-medium">{verifyResult.attribution}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
