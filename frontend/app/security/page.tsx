"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/toaster";
import { api } from "@/lib/api";
import {
    Shield,
    Activity,
    AlertTriangle,
    Ban,
    RefreshCw,
    AlertCircle,
    CheckCircle2,
    Eye
} from "lucide-react";

interface BotActivity {
    total_requests: number;
    bot_percentage: number;
    blocked_count: number;
    suspicious_count: number;
    recent_activity: Array<{
        id: number;
        timestamp: string | null;
        service_id: number;
        service_name: string;
        api_key: string;
        bot_score: number;
        classification: string;
        user_agent: string;
        action_taken: string;
    }>;
}

interface BotBlockingConfig {
    service_id: number;
    service_name: string;
    block_bots_enabled: boolean;
}

export default function SecurityPage() {
    const [botActivity, setBotActivity] = useState<BotActivity | null>(null);
    const [botBlockingConfigs, setBotBlockingConfigs] = useState<BotBlockingConfig[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setIsLoading(true);
        setError(null);

        try {
            const [activityData, configsData] = await Promise.all([
                api.getBotActivity(),
                api.getAllBotBlockingConfigs()
            ]);

            setBotActivity(activityData);
            setBotBlockingConfigs(configsData.services);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Failed to load security data";
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    const handleToggleBotBlocking = async (serviceId: number, enabled: boolean) => {
        try {
            await api.updateBotBlocking(serviceId, enabled);
            toast.success(`Bot blocking ${enabled ? 'enabled' : 'disabled'} successfully`);

            // Update local state
            setBotBlockingConfigs(prev =>
                prev.map(config =>
                    config.service_id === serviceId
                        ? { ...config, block_bots_enabled: enabled }
                        : config
                )
            );
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Failed to update bot blocking";
            toast.error(errorMessage);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const getClassificationBadge = (classification: string) => {
        switch (classification) {
            case 'human':
                return <Badge variant="secondary" className="bg-green-500/10 text-green-700 border-green-500/20">Human</Badge>;
            case 'suspicious':
                return <Badge variant="default" className="bg-yellow-500/10 text-yellow-700 border-yellow-500/20">Suspicious</Badge>;
            case 'bot':
                return <Badge variant="destructive" className="bg-red-500/10 text-red-700 border-red-500/20">Bot</Badge>;
            default:
                return <Badge variant="outline">{classification}</Badge>;
        }
    };

    const getActionBadge = (action: string) => {
        switch (action) {
            case 'allowed':
                return <Badge variant="outline" className="text-xs">Allowed</Badge>;
            case 'flagged':
                return <Badge variant="default" className="text-xs bg-yellow-500/10 text-yellow-700">Flagged</Badge>;
            case 'blocked':
                return <Badge variant="destructive" className="text-xs">Blocked</Badge>;
            default:
                return <Badge variant="outline" className="text-xs">{action}</Badge>;
        }
    };

    return (
        <DashboardLayout>
            <div className="space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <h1 className="text-3xl font-semibold tracking-tight">Security</h1>
                        <p className="text-muted-foreground text-sm">
                            Monitor bot activity and configure automated abuse prevention
                        </p>
                    </div>
                    {!isLoading && (
                        <button
                            onClick={fetchData}
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

                {/* Metrics Section */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {/* Total Requests Analyzed */}
                    <Card className="border-border/50 bg-card/50 backdrop-blur">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                Requests Analyzed
                            </CardTitle>
                            <div className="h-8 w-8 rounded-md bg-blue-500/10 flex items-center justify-center">
                                <Activity className="h-4 w-4 text-blue-500" />
                            </div>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <Skeleton className="h-8 w-20" />
                            ) : (
                                <>
                                    <div className="text-2xl font-semibold tracking-tight">
                                        {botActivity?.total_requests.toLocaleString() || 0}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Total traffic analyzed
                                    </p>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    {/* Bot Traffic % */}
                    <Card className="border-border/50 bg-card/50 backdrop-blur">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                Bot Traffic
                            </CardTitle>
                            <div className="h-8 w-8 rounded-md bg-red-500/10 flex items-center justify-center">
                                <Shield className="h-4 w-4 text-red-500" />
                            </div>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <Skeleton className="h-8 w-20" />
                            ) : (
                                <>
                                    <div className="flex items-baseline gap-2">
                                        <div className="text-2xl font-semibold tracking-tight">
                                            {botActivity?.bot_percentage.toFixed(1) || 0}%
                                        </div>
                                        <Badge
                                            variant={
                                                (botActivity?.bot_percentage || 0) > 20
                                                    ? "destructive"
                                                    : (botActivity?.bot_percentage || 0) > 10
                                                        ? "default"
                                                        : "secondary"
                                            }
                                            className="text-xs"
                                        >
                                            {(botActivity?.bot_percentage || 0) > 20
                                                ? "high"
                                                : (botActivity?.bot_percentage || 0) > 10
                                                    ? "moderate"
                                                    : "low"}
                                        </Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Classified as bots
                                    </p>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    {/* Blocked Requests */}
                    <Card className="border-border/50 bg-card/50 backdrop-blur">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                Blocked Requests
                            </CardTitle>
                            <div className="h-8 w-8 rounded-md bg-amber-500/10 flex items-center justify-center">
                                <Ban className="h-4 w-4 text-amber-500" />
                            </div>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <Skeleton className="h-8 w-20" />
                            ) : (
                                <>
                                    <div className="text-2xl font-semibold tracking-tight">
                                        {botActivity?.blocked_count.toLocaleString() || 0}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Automated abuse blocked
                                    </p>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    {/* Suspicious Activity */}
                    <Card className="border-border/50 bg-card/50 backdrop-blur">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                Suspicious Activity
                            </CardTitle>
                            <div className="h-8 w-8 rounded-md bg-yellow-500/10 flex items-center justify-center">
                                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                            </div>
                        </CardHeader>
                        <CardContent>
                            {isLoading ? (
                                <Skeleton className="h-8 w-20" />
                            ) : (
                                <>
                                    <div className="text-2xl font-semibold tracking-tight">
                                        {botActivity?.suspicious_count.toLocaleString() || 0}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Flagged for review
                                    </p>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Bot Blocking Controls */}
                <Card className="border-border/50 bg-card/50 backdrop-blur">
                    <CardHeader>
                        <CardTitle className="text-base font-semibold">Bot Blocking Controls</CardTitle>
                        <CardDescription className="text-xs">
                            Enable or disable automatic bot blocking per service
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="space-y-3">
                                {[1, 2, 3].map((i) => (
                                    <Skeleton key={i} className="h-16 w-full" />
                                ))}
                            </div>
                        ) : botBlockingConfigs.length > 0 ? (
                            <div className="space-y-3">
                                {botBlockingConfigs.map((config) => (
                                    <div
                                        key={config.service_id}
                                        className="flex items-center justify-between p-4 rounded-md border border-border/50 hover:bg-muted/30 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`h-2 w-2 rounded-full ${config.block_bots_enabled ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                                            <div>
                                                <div className="font-medium text-sm">{config.service_name}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    Service ID: {config.service_id}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs text-muted-foreground">
                                                {config.block_bots_enabled ? 'Blocking enabled' : 'Blocking disabled'}
                                            </span>
                                            <Switch
                                                checked={config.block_bots_enabled}
                                                onCheckedChange={(checked) => handleToggleBotBlocking(config.service_id, checked)}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-32 text-muted-foreground">
                                <div className="text-center space-y-2">
                                    <Shield className="h-8 w-8 mx-auto opacity-50" />
                                    <p className="text-xs">No services registered yet</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Bot Activity Table */}
                <Card className="border-border/50 bg-card/50 backdrop-blur">
                    <CardHeader>
                        <CardTitle className="text-base font-semibold">Recent Bot Activity</CardTitle>
                        <CardDescription className="text-xs">
                            Last 100 requests with bot detection results
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="space-y-3">
                                {[1, 2, 3, 4, 5].map((i) => (
                                    <Skeleton key={i} className="h-12 w-full" />
                                ))}
                            </div>
                        ) : botActivity && botActivity.recent_activity.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead className="border-b border-border/50">
                                        <tr className="text-left">
                                            <th className="pb-3 font-medium text-muted-foreground">Timestamp</th>
                                            <th className="pb-3 font-medium text-muted-foreground">Service</th>
                                            <th className="pb-3 font-medium text-muted-foreground">API Key</th>
                                            <th className="pb-3 font-medium text-muted-foreground">Classification</th>
                                            <th className="pb-3 font-medium text-muted-foreground">Score</th>
                                            <th className="pb-3 font-medium text-muted-foreground">User Agent</th>
                                            <th className="pb-3 font-medium text-muted-foreground">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border/30">
                                        {botActivity.recent_activity.map((activity) => (
                                            <tr key={activity.id} className="hover:bg-muted/30 transition-colors">
                                                <td className="py-3 text-xs text-muted-foreground">
                                                    {activity.timestamp ? new Date(activity.timestamp).toLocaleString() : 'N/A'}
                                                </td>
                                                <td className="py-3 text-xs font-medium">{activity.service_name}</td>
                                                <td className="py-3 text-xs font-mono">{activity.api_key}</td>
                                                <td className="py-3">{getClassificationBadge(activity.classification)}</td>
                                                <td className="py-3">
                                                    <span className={`text-xs font-semibold ${activity.bot_score >= 0.7 ? 'text-red-500' :
                                                            activity.bot_score >= 0.3 ? 'text-yellow-500' :
                                                                'text-green-500'
                                                        }`}>
                                                        {activity.bot_score.toFixed(2)}
                                                    </span>
                                                </td>
                                                <td className="py-3 text-xs text-muted-foreground max-w-xs truncate" title={activity.user_agent}>
                                                    {activity.user_agent || 'N/A'}
                                                </td>
                                                <td className="py-3">{getActionBadge(activity.action_taken)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-32 text-muted-foreground">
                                <div className="text-center space-y-2">
                                    <Eye className="h-8 w-8 mx-auto opacity-50" />
                                    <p className="text-xs">No bot activity detected yet</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
