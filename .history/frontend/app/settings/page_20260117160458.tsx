"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toaster";
import { Skeleton } from "@/components/ui/skeleton";
import { api, getApiKey, setApiKey as saveApiKey } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Shield,
  Eye,
  EyeOff,
  Copy,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Lock,
  Key,
  Clock,
  RefreshCw,
  Ban,
  Loader2,
  Plus,
  X,
  Fingerprint,
  Search,
  ToggleLeft,
  ToggleRight
} from "lucide-react";

interface ApiKeyData {
  id: number;
  key_masked: string;
  created_at: string | null;
  is_active: boolean;
  rate_limit_requests?: number | null;
  rate_limit_window_seconds?: number | null;
}

interface ServiceApiKeys {
  service_id: number;
  service_name: string;
  api_keys: ApiKeyData[];
}

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

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("");
  const [isRevealed, setIsRevealed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [servicesApiKeys, setServicesApiKeys] = useState<ServiceApiKeys[]>([]);
  const [isLoadingApiKeys, setIsLoadingApiKeys] = useState(true);
  const [copiedKeyId, setCopiedKeyId] = useState<number | null>(null);
  const [revokingKeyId, setRevokingKeyId] = useState<number | null>(null);
  
  // Rate limit editing state: key_id -> { requests, window_seconds }
  const [rateLimitEdits, setRateLimitEdits] = useState<Record<number, { requests: string; windowSeconds: string }>>({});
  const [savingKeyId, setSavingKeyId] = useState<number | null>(null);
  
  // Modal state for new API key
  const [newApiKeyModal, setNewApiKeyModal] = useState<{
    isOpen: boolean;
    apiKey: string;
    serviceId: number;
    serviceName: string;
  } | null>(null);
  const [isGeneratingKey, setIsGeneratingKey] = useState(false);
  const [newKeyCopied, setNewKeyCopied] = useState(false);

  // Data Protection / Watermarking state
  const [services, setServices] = useState<ServiceData[]>([]);
  const [isLoadingServices, setIsLoadingServices] = useState(true);
  const [togglingServiceId, setTogglingServiceId] = useState<number | null>(null);
  const [verifyInput, setVerifyInput] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<WatermarkResult | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  // Load API key from localStorage on mount
  useEffect(() => {
    const storedApiKey = getApiKey();
    if (storedApiKey) {
      setApiKey(storedApiKey);
    }
  }, []);

  // Load API keys per service on mount
  useEffect(() => {
    fetchApiKeys();
  }, []);

  // Load services for watermarking on mount
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
      // Update local state
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

  const fetchApiKeys = async () => {
    setIsLoadingApiKeys(true);
    try {
      const data = await api.listAllApiKeys();
      setServicesApiKeys(data.services);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load API keys";
      toast.error(errorMessage);
    } finally {
      setIsLoadingApiKeys(false);
    }
  };

  const handleFetchApiKey = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.getMyApiKey();
      
      if (data.api_key) {
        setApiKey(data.api_key);
        setIsRevealed(true);
        saveApiKey(data.api_key);
        toast.success("API key retrieved successfully");
      } else if (data.message) {
        setError(data.message);
        toast.warning(data.message);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "An error occurred";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleReveal = () => {
    if (!apiKey && !isRevealed) {
      handleFetchApiKey();
    } else {
      setIsRevealed(!isRevealed);
    }
  };

  const copyToClipboard = () => {
    const textToCopy = apiKey;
    if (!textToCopy) {
      toast.error("No API key available to copy");
      return;
    }
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    toast.success("API key copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const copyApiKeyMasked = (keyMasked: string, keyId: number) => {
    navigator.clipboard.writeText(keyMasked);
    setCopiedKeyId(keyId);
    toast.success("API key masked value copied to clipboard");
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  const handleRevokeKey = async (serviceId: number, keyId: number) => {
    if (!confirm("Are you sure you want to revoke this API key? It will no longer be valid for authentication.")) {
      return;
    }

    setRevokingKeyId(keyId);
    try {
      await api.revokeApiKey(serviceId, keyId);
      toast.success("API key revoked successfully");
      // Refresh the API keys list
      await fetchApiKeys();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to revoke API key";
      toast.error(errorMessage);
    } finally {
      setRevokingKeyId(null);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A";
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  const handleRateLimitChange = (keyId: number, field: "requests" | "windowSeconds", value: string) => {
    setRateLimitEdits((prev) => ({
      ...prev,
      [keyId]: {
        ...prev[keyId],
        [field]: value,
      },
    }));
  };

  const getRateLimitValue = (keyData: ApiKeyData, field: "requests" | "windowSeconds"): string => {
    const keyId = keyData.id;
    if (rateLimitEdits[keyId]) {
      return rateLimitEdits[keyId][field] || "";
    }
    if (field === "requests") {
      return keyData.rate_limit_requests?.toString() || "";
    }
    return keyData.rate_limit_window_seconds?.toString() || "";
  };

  const hasEdits = (keyId: number): boolean => {
    return !!rateLimitEdits[keyId];
  };

  const handleSaveRateLimit = async (keyId: number, event?: React.MouseEvent<HTMLButtonElement>) => {
    // Prevent form submission if button is inside a form
    if (event) {
      event.preventDefault();
    }

    const edit = rateLimitEdits[keyId];
    if (!edit) return;

    const requests = parseInt(edit.requests, 10);
    const windowSeconds = parseInt(edit.windowSeconds, 10);

    console.log("SAVE CLICKED", keyId, requests, windowSeconds);

    if (isNaN(requests) || requests <= 0) {
      toast.error("Requests must be a positive number");
      return;
    }
    if (isNaN(windowSeconds) || windowSeconds <= 0) {
      toast.error("Window seconds must be a positive number");
      return;
    }

    setSavingKeyId(keyId);
    try {
      await api.updateApiKeyRateLimit(keyId, requests, windowSeconds);
      toast.success("Rate limit updated successfully");

      // Update UI state immediately
      setServicesApiKeys((prev) =>
        prev.map((service) => ({
          ...service,
          api_keys: service.api_keys.map((key) =>
            key.id === keyId
              ? {
                  ...key,
                  rate_limit_requests: requests,
                  rate_limit_window_seconds: windowSeconds,
                }
              : key
          ),
        }))
      );

      // Clear the edit state for this key
      setRateLimitEdits((prev) => {
        const next = { ...prev };
        delete next[keyId];
        return next;
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to update rate limit";
      toast.error(errorMessage);
    } finally {
      setSavingKeyId(null);
    }
  };

  const handleGenerateNewKey = async (serviceId: number, serviceName: string) => {
    setIsGeneratingKey(true);
    try {
      const data = await api.createServiceApiKey(serviceId);
      
      // Show modal with new key
      setNewApiKeyModal({
        isOpen: true,
        apiKey: data.api_key,
        serviceId: serviceId,
        serviceName: serviceName,
      });
      
      // Refresh the API keys list to show the new key
      await fetchApiKeys();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to generate API key";
      toast.error(errorMessage);
    } finally {
      setIsGeneratingKey(false);
    }
  };

  const copyNewApiKey = () => {
    if (newApiKeyModal) {
      navigator.clipboard.writeText(newApiKeyModal.apiKey);
      setNewKeyCopied(true);
      toast.success("API key copied to clipboard");
      setTimeout(() => setNewKeyCopied(false), 2000);
    }
  };

  const closeNewKeyModal = () => {
    setNewApiKeyModal(null);
    setNewKeyCopied(false);
  };

  const maskedKey = "••••••••••••••••••••••••••••••••••••••••";
  const displayKey = isRevealed && apiKey ? apiKey : maskedKey;

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">Security Settings</h1>
          <p className="text-muted-foreground text-sm">
            Manage your API keys and security policies
          </p>
        </div>

        {/* API Key Management */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                  <Key className="h-5 w-5 text-amber-500" />
                </div>
                <div>
                  <CardTitle>API Key</CardTitle>
                  <CardDescription className="text-xs">
                    Your gateway authentication key
                  </CardDescription>
                </div>
              </div>
              <Badge variant="secondary" className="gap-1.5">
                <Lock className="h-3 w-3" />
                Sensitive
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Security Warning */}
            <Alert className="border-amber-500/50 bg-amber-500/5">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <AlertDescription className="text-sm text-amber-600 dark:text-amber-400">
                <strong>Important:</strong> Keep your API key secure and never share it publicly. 
                Exposed keys can be used to access your gateway services.
              </AlertDescription>
            </Alert>

            {/* API Key Display */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Your API Key</Label>
              <div className="flex items-center gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={isRevealed && apiKey ? "text" : "password"}
                    value={displayKey}
                    readOnly
                    className="font-mono text-sm bg-muted/50 pr-20 border-border/50"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleReveal}
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7 text-muted-foreground hover:text-foreground transition-colors hover:bg-muted/50"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : isRevealed && apiKey ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <Button
                  variant="outline"
                  onClick={copyToClipboard}
                  disabled={!isRevealed || !apiKey}
                  className="shrink-0 transition-all hover:scale-105 hover:shadow-md"
                >
                  {copied ? (
                    <>
                      <CheckCircle2 className="mr-2 h-4 w-4 text-green-500" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                {isRevealed && apiKey
                  ? "Your API key is visible. Keep it secure and never share it."
                  : apiKey 
                    ? "Click the eye icon to reveal your API key"
                    : "Click the eye icon to fetch your API key from the server"}
              </p>
            </div>

            {/* Error State */}
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* API Keys per Service */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Key className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>API Keys by Service</CardTitle>
                  <CardDescription className="text-xs">
                    Manage API keys for each service
                  </CardDescription>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchApiKeys}
                disabled={isLoadingApiKeys}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoadingApiKeys ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingApiKeys ? (
              <div className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : servicesApiKeys.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Key className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <p className="text-sm font-medium mb-1">No API keys found</p>
                <p className="text-xs text-muted-foreground">
                  Register a service to start creating API keys
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {servicesApiKeys.map((service) => (
                  <div key={service.service_id} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <h3 className="text-base font-semibold">{service.service_name}</h3>
                        <Badge variant="outline" className="text-xs">
                          {service.api_keys.length} key{service.api_keys.length !== 1 ? 's' : ''}
                        </Badge>
                      </div>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleGenerateNewKey(service.service_id, service.service_name)}
                        disabled={isGeneratingKey}
                        className="gap-2"
                      >
                        {isGeneratingKey ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <Plus className="h-4 w-4" />
                            Generate New API Key
                          </>
                        )}
                      </Button>
                    </div>
                    
                    {service.api_keys.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4">
                        No API keys for this service yet
                      </p>
                    ) : (
                      <div className="rounded-md border border-border overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-[200px]">API Key</TableHead>
                              <TableHead>Created</TableHead>
                              <TableHead className="w-[100px]">Status</TableHead>
                              <TableHead className="w-[120px]">Rate Limit (req)</TableHead>
                              <TableHead className="w-[120px]">Rate Limit (sec)</TableHead>
                              <TableHead className="w-[200px] text-right">Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {service.api_keys.map((keyData) => (
                              <TableRow key={keyData.id}>
                                <TableCell>
                                  <code className="text-xs font-mono bg-muted px-2 py-1 rounded">
                                    {keyData.key_masked}
                                  </code>
                                </TableCell>
                                <TableCell className="text-sm text-muted-foreground">
                                  {formatDate(keyData.created_at)}
                                </TableCell>
                                <TableCell>
                                  <Badge
                                    variant={keyData.is_active ? "default" : "secondary"}
                                    className={
                                      keyData.is_active
                                        ? "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
                                        : "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20"
                                    }
                                  >
                                    {keyData.is_active ? "Active" : "Revoked"}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <Input
                                    type="number"
                                    min="1"
                                    value={getRateLimitValue(keyData, "requests")}
                                    onChange={(e) => handleRateLimitChange(keyData.id, "requests", e.target.value)}
                                    placeholder="10"
                                    disabled={!keyData.is_active}
                                    className="h-8 w-full text-sm"
                                  />
                                </TableCell>
                                <TableCell>
                                  <Input
                                    type="number"
                                    min="1"
                                    value={getRateLimitValue(keyData, "windowSeconds")}
                                    onChange={(e) => handleRateLimitChange(keyData.id, "windowSeconds", e.target.value)}
                                    placeholder="60"
                                    disabled={!keyData.is_active}
                                    className="h-8 w-full text-sm"
                                  />
                                </TableCell>
                                <TableCell className="text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    {hasEdits(keyData.id) && (
                                      <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={(e) => handleSaveRateLimit(keyData.id, e)}
                                        disabled={!keyData.is_active || savingKeyId === keyData.id}
                                        className="h-8 px-2 text-xs"
                                      >
                                        {savingKeyId === keyData.id ? (
                                          <Loader2 className="h-3 w-3 animate-spin" />
                                        ) : (
                                          "Save"
                                        )}
                                      </Button>
                                    )}
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => copyApiKeyMasked(keyData.key_masked, keyData.id)}
                                      disabled={!keyData.is_active}
                                      className="h-8 px-2"
                                    >
                                      {copiedKeyId === keyData.id ? (
                                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                                      ) : (
                                        <Copy className="h-4 w-4" />
                                      )}
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleRevokeKey(service.service_id, keyData.id)}
                                      disabled={!keyData.is_active || revokingKeyId === keyData.id}
                                      className="h-8 px-2 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                                    >
                                      {revokingKeyId === keyData.id ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                      ) : (
                                        <Ban className="h-4 w-4" />
                                      )}
                                    </Button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Rate Limit Policy */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Clock className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <CardTitle>Rate Limit Policy</CardTitle>
                <CardDescription className="text-xs">
                  Current rate limiting configuration
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Requests per Window</span>
                  <Badge variant="outline">10 requests</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Maximum number of requests allowed per rate limit window
                </p>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Time Window</span>
                  <Badge variant="outline">60 seconds</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Duration of each rate limit window before reset
                </p>
              </div>
            </div>

            <div className="rounded-md border border-border/50 bg-muted/30 p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Policy Details</span>
              </div>
              <ul className="text-xs text-muted-foreground space-y-1.5 ml-6 list-disc">
                <li>Rate limits are enforced per API key</li>
                <li>Requests exceeding the limit will receive HTTP 429 responses</li>
                <li>Token bucket algorithm ensures fair distribution of requests</li>
                <li>Tokens refill continuously based on elapsed time</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Data Protection / Watermarking */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Fingerprint className="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <CardTitle>Data Protection</CardTitle>
                <CardDescription className="text-xs">
                  Watermark responses for leak attribution and tracing
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Explanation */}
            <Alert className="border-purple-500/50 bg-purple-500/5">
              <Fingerprint className="h-4 w-4 text-purple-500" />
              <AlertDescription className="text-sm text-purple-600 dark:text-purple-400">
                <strong>Response Watermarking:</strong> When enabled, each API response is embedded with a unique, 
                traceable watermark containing the service ID, API key ID, request ID, and timestamp. 
                If data is leaked, you can trace it back to the source.
              </AlertDescription>
            </Alert>

            {/* Per-Service Watermarking Toggle */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Service Watermarking</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={fetchServices}
                  disabled={isLoadingServices}
                >
                  <RefreshCw className={`h-4 w-4 ${isLoadingServices ? "animate-spin" : ""}`} />
                </Button>
              </div>

              {isLoadingServices ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : services.length === 0 ? (
                <div className="rounded-md border border-dashed border-border/50 p-6 text-center">
                  <p className="text-sm text-muted-foreground">
                    No services registered. Register an API to enable watermarking.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {services.map((service) => (
                    <div
                      key={service.id}
                      className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 p-4"
                    >
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{service.name}</p>
                        <p className="text-xs text-muted-foreground truncate max-w-[300px]">
                          {service.target_url}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={service.watermarking_enabled ? "default" : "secondary"}
                          className={service.watermarking_enabled ? "bg-purple-500/20 text-purple-500 border-purple-500/30" : ""}
                        >
                          {service.watermarking_enabled ? "Enabled" : "Disabled"}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleWatermarking(service.id, service.watermarking_enabled)}
                          disabled={togglingServiceId === service.id}
                          className="h-8 w-8 p-0"
                        >
                          {togglingServiceId === service.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : service.watermarking_enabled ? (
                            <ToggleRight className="h-5 w-5 text-purple-500" />
                          ) : (
                            <ToggleLeft className="h-5 w-5 text-muted-foreground" />
                          )}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Example Responses */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium">Example Watermarked Response</h3>
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
  "_gaas_watermark": "MXwyfGFiY2QxMjM0fDIwMjYtMDEtMTdUMTI6MDA6MDBa"
}`}
                  </pre>
                </div>
              </div>
            </div>

            {/* Verify Leaked Data */}
            <div className="space-y-3 pt-2 border-t border-border/50">
              <div className="flex items-center gap-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">Verify Leaked Data</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Paste leaked response data below to extract and decode the watermark. 
                This will reveal which API key accessed the data and when.
              </p>
              <Textarea
                placeholder={`Paste leaked data here...\n\nExample:\n{"id": 1, "name": "Product", "_gaas_watermark": "MXwyfGFiY2..."}`}
                value={verifyInput}
                onChange={(e) => setVerifyInput(e.target.value)}
                className="min-h-[120px] font-mono text-xs"
              />
              <Button
                onClick={handleVerifyWatermark}
                disabled={isVerifying || !verifyInput.trim()}
                className="w-full"
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

              {/* Verification Results */}
              {verifyError && (
                <Alert className="border-red-500/50 bg-red-500/5">
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <AlertDescription className="text-sm text-red-600 dark:text-red-400">
                    {verifyError}
                  </AlertDescription>
                </Alert>
              )}

              {verifyResult && (
                <div className="rounded-md border border-green-500/50 bg-green-500/5 p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-sm font-medium text-green-600 dark:text-green-400">
                      Watermark Found & Decoded
                    </span>
                  </div>
                  
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Service</p>
                      <p className="text-sm font-medium">
                        {verifyResult.decoded.service_name} (ID: {verifyResult.decoded.service_id})
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">API Key</p>
                      <p className="text-sm font-mono">
                        {verifyResult.decoded.api_key_masked} (ID: {verifyResult.decoded.api_key_id})
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Request ID</p>
                      <p className="text-sm font-mono">{verifyResult.decoded.request_id}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Timestamp</p>
                      <p className="text-sm">{verifyResult.decoded.timestamp}</p>
                    </div>
                  </div>

                  <div className="rounded-md bg-muted/50 p-3 mt-2">
                    <p className="text-xs text-muted-foreground mb-1">Attribution</p>
                    <p className="text-sm">{verifyResult.attribution}</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Security Best Practices */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                <Shield className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <CardTitle>Security Best Practices</CardTitle>
                <CardDescription className="text-xs">
                  Recommendations for keeping your API secure
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-md bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Lock className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-1">Store Securely</p>
                    <p className="text-xs text-muted-foreground">
                      Store API keys in environment variables or secure secret management systems. 
                      Never commit keys to version control.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-md bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Key className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-1">Rotate Regularly</p>
                    <p className="text-xs text-muted-foreground">
                      Rotate your API keys periodically to minimize the impact of potential leaks. 
                      Generate new keys when team members leave.
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-md bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-1">Monitor Usage</p>
                    <p className="text-xs text-muted-foreground">
                      Regularly monitor API usage patterns. Unusual spikes may indicate 
                      key compromise or abuse.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-md bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Shield className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-1">Use HTTPS</p>
                    <p className="text-xs text-muted-foreground">
                      Always use HTTPS when making requests to the gateway. 
                      Never transmit API keys over unencrypted connections.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* New API Key Modal */}
        {newApiKeyModal && newApiKeyModal.isOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <Card className="w-full max-w-lg mx-4 border-amber-500/50 bg-card shadow-xl">
              <CardHeader className="border-b border-border">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                      <Key className="h-5 w-5 text-amber-500" />
                    </div>
                    <div>
                      <CardTitle>New API Key Generated</CardTitle>
                      <CardDescription className="text-xs">
                        {newApiKeyModal.serviceName}
                      </CardDescription>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={closeNewKeyModal}
                    className="h-8 w-8"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-6">
                {/* Security Warning */}
                <Alert className="border-amber-500/50 bg-amber-500/5">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <AlertDescription className="text-sm text-amber-600 dark:text-amber-400">
                    <strong>Important:</strong> This API key will only be shown once. 
                    Make sure to copy and store it securely. You won't be able to view it again.
                  </AlertDescription>
                </Alert>

                {/* API Key Display */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Your New API Key</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="text"
                      value={newApiKeyModal.apiKey}
                      readOnly
                      className="font-mono text-sm bg-muted/50 border-amber-500/50"
                    />
                    <Button
                      variant="outline"
                      onClick={copyNewApiKey}
                      className="shrink-0"
                    >
                      {newKeyCopied ? (
                        <>
                          <CheckCircle2 className="mr-2 h-4 w-4 text-green-500" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="mr-2 h-4 w-4" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Store this key in a secure location. It cannot be retrieved again.
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-2">
                  <Button
                    variant="default"
                    onClick={closeNewKeyModal}
                    className="flex-1"
                  >
                    I've Saved My Key
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
