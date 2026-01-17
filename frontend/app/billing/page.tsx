"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "@/components/ui/toaster";
import { api, ApiRequestError } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DollarSign,
  TrendingUp,
  RefreshCw,
  Loader2,
  AlertCircle,
  CreditCard,
  ArrowRight,
  Activity,
  FileText,
  X,
  Calendar
} from "lucide-react";
import { Input } from "@/components/ui/input";

interface BillingApiKey {
  api_key_id: number;
  service_name: string;
  requests_used: number;
  price_per_request: number;
  total_cost: number;
}

interface BillingData {
  api_keys: BillingApiKey[];
}

interface BillingSummary {
  total_requests: number;
  total_cost: number;
  cost_this_month: number;
}

export default function BillingPage() {
  const [billingData, setBillingData] = useState<BillingData | null>(null);
  const [billingSummary, setBillingSummary] = useState<BillingSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingSummary, setIsLoadingSummary] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  
  // Price editing state: key_id -> { price: string, isSaving: boolean }
  const [priceEdits, setPriceEdits] = useState<Record<number, { price: string; isSaving: boolean }>>({});

  useEffect(() => {
    fetchBillingSummary();
    fetchBillingData();
  }, []);

  const fetchBillingSummary = async () => {
    setIsLoadingSummary(true);
    setSummaryError(null);

    try {
      const data = await api.getBillingSummary();
      setBillingSummary(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load billing summary";
      setSummaryError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoadingSummary(false);
    }
  };

  const fetchBillingData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await api.getBillingApiKeys();
      setBillingData(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load billing data";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetBilling = async () => {
    if (!confirm("Are you sure you want to start a new billing cycle? This will reset all API key costs to $0.")) {
      return;
    }

    setIsResetting(true);
    try {
      await api.resetBilling();
      toast.success("New billing cycle started successfully");
      await Promise.all([fetchBillingSummary(), fetchBillingData()]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to reset billing cycle";
      toast.error(errorMessage);
    } finally {
      setIsResetting(false);
    }
  };

  // Get metrics from summary data
  const totalRequests = billingSummary?.total_requests || 0;
  const totalCost = billingSummary?.total_cost || 0;
  const costThisMonth = billingSummary?.cost_this_month || 0;

  const handlePriceChange = (keyId: number, value: string) => {
    setPriceEdits((prev) => ({
      ...prev,
      [keyId]: {
        ...prev[keyId],
        price: value,
      },
    }));
  };

  const getPriceValue = (key: BillingApiKey): string => {
    if (priceEdits[key.api_key_id]?.price !== undefined && priceEdits[key.api_key_id].price !== null) {
      return priceEdits[key.api_key_id].price || "";
    }
    // Always return a string, never undefined
    return (key.price_per_request ?? 0.001).toString();
  };

  const hasPriceEdit = (keyId: number): boolean => {
    const edit = priceEdits[keyId];
    if (!edit?.price) return false;
    
    // Check if price differs from original
    const originalKey = billingData?.api_keys.find(k => k.api_key_id === keyId);
    const originalPrice = originalKey?.price_per_request.toString() || "";
    if (edit.price === originalPrice) return false;
    
    // Check if value is a valid positive number
    const numPrice = parseFloat(edit.price);
    if (isNaN(numPrice) || numPrice <= 0) return false;
    
    return true;
  };

  const validatePrice = (price: string): string | null => {
    if (!price || price.trim() === "") {
      return "Price is required";
    }
    
    const numPrice = parseFloat(price);
    
    if (isNaN(numPrice)) {
      return "Price must be a valid number";
    }
    
    if (numPrice <= 0) {
      return "Price must be greater than 0";
    }
    
    // Check decimal places
    const decimalPlaces = price.includes('.') ? price.split('.')[1].length : 0;
    if (decimalPlaces > 3) {
      return "Price must have at most 3 decimal places";
    }
    
    return null;
  };

  const handleSavePrice = async (keyId: number) => {
    const edit = priceEdits[keyId];
    
    // Get the original price for reference
    const originalKey = billingData?.api_keys.find(k => k.api_key_id === keyId);
    const originalPrice = originalKey?.price_per_request || 0.001;
    
    // Parse price value - ensure it's a number, not a string
    let priceValue: number;
    if (edit?.price) {
      const parsed = Number(edit.price);
      // Ensure it's a valid number (not NaN)
      if (isNaN(parsed)) {
        // If invalid, use original price - backend will validate
        priceValue = originalPrice;
      } else {
        priceValue = parsed;
      }
    } else {
      // No edit, use original - backend will handle validation
      priceValue = originalPrice;
    }

    // Log before sending - exact format requested: PRICING SAVE CLICKED, key_id, price
    console.log(`PRICING SAVE CLICKED, ${keyId}, ${priceValue}`);

    setPriceEdits((prev) => ({
      ...prev,
      [keyId]: { ...prev[keyId], isSaving: true },
    }));

    try {
      // Always send the request - no early returns, backend will validate
      const response = await api.updateApiKeyPrice(keyId, priceValue);
      
      // Log successful response
      console.log(`PRICING SAVE SUCCESS, key_id=${keyId}, response:`, response);
      
      toast.success("Price per request updated successfully");

      // Update UI state immediately with the response value
      setBillingData((prev) =>
        prev
          ? {
              ...prev,
              api_keys: prev.api_keys.map((key) =>
                key.api_key_id === keyId
                  ? { ...key, price_per_request: response.price_per_request }
                  : key
              ),
            }
          : null
      );

      // Clear the edit state
      setPriceEdits((prev) => {
        const next = { ...prev };
        delete next[keyId];
        return next;
      });
    } catch (err) {
      // Log error
      console.error(`PRICING SAVE ERROR, key_id=${keyId}:`, err);
      
      // Extract error message from response - ApiRequestError contains the detail
      let errorMessage = "Failed to update price";
      if (err instanceof ApiRequestError) {
        errorMessage = err.message; // This contains the detail from backend
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      toast.error(errorMessage);
    } finally {
      setPriceEdits((prev) => ({
        ...prev,
        [keyId]: { ...prev[keyId], isSaving: false },
      }));
    }
  };

  // Group usage by service
  const usageByService = billingData?.api_keys.reduce((acc, key) => {
    const existing = acc.find(s => s.service_name === key.service_name);
    if (existing) {
      existing.requests += key.requests_used;
      existing.cost += key.total_cost;
    } else {
      acc.push({
        service_name: key.service_name,
        requests: key.requests_used,
        cost: key.total_cost,
      });
    }
    return acc;
  }, [] as Array<{ service_name: string; requests: number; cost: number }>) || [];

  // Format currency (3 decimal places for billing display)
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    }).format(amount);
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-semibold tracking-tight">Billing</h1>
            <p className="text-muted-foreground text-sm">
              Monitor usage and costs across all API keys
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              fetchBillingSummary();
              fetchBillingData();
            }}
            disabled={isLoading || isLoadingSummary}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${(isLoading || isLoadingSummary) ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Error States */}
        {summaryError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Summary: {summaryError}</AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Details: {error}</AlertDescription>
          </Alert>
        )}

        {/* Billing Overview */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="text-2xl font-bold">{totalRequests.toLocaleString()}</div>
              )}
              <p className="text-xs text-muted-foreground mt-1">All time</p>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="text-2xl font-bold">{formatCurrency(totalCost)}</div>
              )}
              <p className="text-xs text-muted-foreground mt-1">Accumulated</p>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cost This Month</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {isLoadingSummary ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="text-2xl font-bold">{formatCurrency(costThisMonth)}</div>
              )}
              <p className="text-xs text-muted-foreground mt-1">Current cycle</p>
            </CardContent>
          </Card>
        </div>

        {/* Billing Actions */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <h3 className="text-sm font-semibold">Billing Cycle Management</h3>
                <p className="text-xs text-muted-foreground">
                  Start a new billing cycle to reset all API key costs
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowInvoiceModal(true)}
                  disabled={isLoading || isLoadingSummary}
                  className="gap-2"
                >
                  <FileText className="h-4 w-4" />
                  View Sample Invoice
                </Button>
                <Button
                  variant="default"
                  onClick={handleResetBilling}
                  disabled={isResetting || isLoading}
                  className="gap-2"
                >
                  {isResetting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Resetting...
                    </>
                  ) : (
                    <>
                      <CreditCard className="h-4 w-4" />
                      New Billing Cycle
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Usage by Service */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Activity className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle>Usage by Service</CardTitle>
                <CardDescription className="text-xs">
                  Aggregated request counts and costs per service
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : usageByService.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Activity className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <p className="text-sm font-medium mb-1">No usage data</p>
                <p className="text-xs text-muted-foreground">
                  Usage data will appear here as API keys are used
                </p>
              </div>
            ) : (
              <div className="rounded-md border border-border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[300px]">Service Name</TableHead>
                      <TableHead className="text-right">Requests</TableHead>
                      <TableHead className="text-right">Cost</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {usageByService.map((service, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-medium">{service.service_name}</TableCell>
                        <TableCell className="text-right">
                          {service.requests.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-semibold">
                          {formatCurrency(service.cost)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* API Key Billing */}
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <CreditCard className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle>API Key Billing</CardTitle>
                <CardDescription className="text-xs">
                  Detailed billing information per API key
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : !billingData || billingData.api_keys.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CreditCard className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                <p className="text-sm font-medium mb-1">No API keys</p>
                <p className="text-xs text-muted-foreground">
                  Create API keys to see billing information
                </p>
              </div>
            ) : (
              <div className="rounded-md border border-border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[200px]">API Key</TableHead>
                      <TableHead>Service</TableHead>
                      <TableHead className="w-[150px]">Price/Request</TableHead>
                      <TableHead className="text-right">Requests</TableHead>
                      <TableHead className="text-right">Cost</TableHead>
                      <TableHead className="w-[100px] text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {billingData.api_keys.map((key) => (
                      <TableRow key={key.api_key_id}>
                        <TableCell>
                          <code className="text-xs font-mono bg-muted px-2 py-1 rounded">
                            {`key_${key.api_key_id}••••`}
                          </code>
                        </TableCell>
                        <TableCell className="font-medium">{key.service_name}</TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            step="0.001"
                            min="0.001"
                            value={getPriceValue(key)}
                            onChange={(e) => handlePriceChange(key.api_key_id, e.target.value)}
                            className="h-8 w-full text-sm"
                            placeholder="0.001"
                          />
                        </TableCell>
                        <TableCell className="text-right">
                          {key.requests_used.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-semibold">
                          {formatCurrency(key.total_cost)}
                        </TableCell>
                        <TableCell className="text-right">
                          {hasPriceEdit(key.api_key_id) && (
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => handleSavePrice(key.api_key_id)}
                              disabled={priceEdits[key.api_key_id]?.isSaving}
                              className="h-8 px-2 text-xs"
                            >
                              {priceEdits[key.api_key_id]?.isSaving ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                "Save"
                              )}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Sample Invoice Modal */}
        {showInvoiceModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <Card className="w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto border-border bg-card shadow-xl">
              <CardHeader className="border-b border-border">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle>Sample Invoice</CardTitle>
                      <CardDescription className="text-xs">
                        Demo invoice for billing period
                      </CardDescription>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowInvoiceModal(false)}
                    className="h-8 w-8"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6 pt-6">
                {/* Invoice Header */}
                <div className="flex items-center justify-between border-b border-border pb-4">
                  <div>
                    <h2 className="text-2xl font-bold">GaaS Gateway</h2>
                    <p className="text-sm text-muted-foreground mt-1">Gateway-as-a-Service Platform</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">Invoice #INV-{new Date().getFullYear()}-{String(new Date().getMonth() + 1).padStart(2, '0')}-{String(Math.floor(Math.random() * 1000)).padStart(3, '0')}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                    </p>
                  </div>
                </div>

                {/* Date Range */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>Billing Period</span>
                  </div>
                  <div className="pl-6 text-sm text-muted-foreground">
                    {(() => {
                      const now = new Date();
                      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
                      const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                      return `${firstDay.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} - ${lastDay.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`;
                    })()}
                  </div>
                </div>

                {/* Services Used */}
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold">Services Used</h3>
                  <div className="rounded-md border border-border overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Service Name</TableHead>
                          <TableHead className="text-right">Requests</TableHead>
                          <TableHead className="text-right">Cost</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {usageByService.length > 0 ? (
                          usageByService.map((service, index) => (
                            <TableRow key={index}>
                              <TableCell className="font-medium">{service.service_name}</TableCell>
                              <TableCell className="text-right">{service.requests.toLocaleString()}</TableCell>
                              <TableCell className="text-right">{formatCurrency(service.cost)}</TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell colSpan={3} className="text-center text-sm text-muted-foreground py-4">
                              No services used in this period
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </div>

                {/* Summary */}
                <div className="border-t border-border pt-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Total Requests</span>
                    <span className="font-medium">{totalRequests.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Subtotal</span>
                    <span className="font-medium">{formatCurrency(totalCost)}</span>
                  </div>
                  <div className="flex items-center justify-between text-lg font-bold pt-2 border-t border-border">
                    <span>Total</span>
                    <span>{formatCurrency(totalCost)}</span>
                  </div>
                </div>

                {/* Footer Note */}
                <div className="pt-4 border-t border-border">
                  <p className="text-xs text-muted-foreground text-center italic">
                    This is a simulated invoice for demonstration purposes only.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
