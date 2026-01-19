"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "@/components/ui/toaster";
import { api } from "@/lib/api";
import { verifyMerkleRoot } from "@/lib/merkle";
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
    Copy,
    CheckCircle2,
    AlertCircle,
    RefreshCw,
    Loader2,
    FileCheck2,
    Clock,
    Hash,
    ChevronLeft,
    ChevronRight
} from "lucide-react";

interface MerkleRootData {
    batch_id: number;
    merkle_root: string;
    start_time: string;
    end_time: string;
    request_count: number;
    created_at: string;
}

interface MerkleHistoryData {
    merkle_roots: MerkleRootData[];
    total: number;
    limit: number;
    offset: number;
}

export default function TransparencyPage() {
    const [latestRoot, setLatestRoot] = useState<MerkleRootData | null>(null);
    const [history, setHistory] = useState<MerkleHistoryData | null>(null);
    const [isLoadingLatest, setIsLoadingLatest] = useState(true);
    const [isLoadingHistory, setIsLoadingHistory] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [copiedRoot, setCopiedRoot] = useState<number | null>(null);
    const [isVerifying, setIsVerifying] = useState(false);
    const [verificationResult, setVerificationResult] = useState<{
        batchId: number;
        verified: boolean;
        isBlockchain?: boolean;
        txHash?: string;
        blockNumber?: number;
        etherscanUrl?: string;
    } | null>(null);

    // Pagination
    const [currentPage, setCurrentPage] = useState(0);
    const pageSize = 10;

    useEffect(() => {
        fetchLatestRoot();
        fetchHistory(0);
    }, []);

    const fetchLatestRoot = async () => {
        setIsLoadingLatest(true);
        setError(null);

        try {
            const data = await api.getMerkleLatest();
            setLatestRoot(data);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Failed to load latest Merkle root";
            setError(errorMessage);
            // Don't show toast for 404 (no roots yet)
            if (!errorMessage.includes("404")) {
                toast.error(errorMessage);
            }
        } finally {
            setIsLoadingLatest(false);
        }
    };

    const fetchHistory = async (page: number) => {
        setIsLoadingHistory(true);

        try {
            const offset = page * pageSize;
            const data = await api.getMerkleHistory(pageSize, offset);
            setHistory(data);
            setCurrentPage(page);
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Failed to load Merkle history";
            toast.error(errorMessage);
        } finally {
            setIsLoadingHistory(false);
        }
    };

    const handleVerify = async (batchId: number) => {
        setIsVerifying(true);
        setVerificationResult(null);

        try {
            // First, check if this batch is anchored to blockchain
            const blockchainProof = await api.getBlockchainProof(batchId);

            if (blockchainProof.is_anchored) {
                // Blockchain verification - fetch on-chain data
                const batchData = await api.verifyMerkleBatch(batchId);
                const verified = await verifyMerkleRoot(batchData.hashes, batchData.expected_root);

                setVerificationResult({
                    batchId,
                    verified,
                    isBlockchain: true,
                    txHash: blockchainProof.tx_hash,
                    blockNumber: blockchainProof.block_number,
                    etherscanUrl: blockchainProof.etherscan_url
                });

                if (verified) {
                    toast.success(`Batch ${batchId} verified on blockchain! ✓`);
                } else {
                    toast.error(`Batch ${batchId} blockchain verification failed! ✗`);
                }
            } else {
                // Local verification - not yet anchored
                const data = await api.verifyMerkleBatch(batchId);
                const verified = await verifyMerkleRoot(data.hashes, data.expected_root);

                setVerificationResult({
                    batchId,
                    verified,
                    isBlockchain: false
                });

                if (verified) {
                    toast.success(`Batch ${batchId} verified locally! ✓ (Not yet on blockchain)`);
                } else {
                    toast.error(`Batch ${batchId} verification failed! ✗`);
                }
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Verification failed";
            toast.error(errorMessage);
        } finally {
            setIsVerifying(false);
        }
    };

    const copyToClipboard = (text: string, batchId: number) => {
        navigator.clipboard.writeText(text);
        setCopiedRoot(batchId);
        toast.success("Merkle root copied to clipboard");
        setTimeout(() => setCopiedRoot(null), 2000);
    };

    const formatDate = (dateString: string) => {
        try {
            return new Date(dateString).toLocaleString();
        } catch {
            return dateString;
        }
    };

    const formatTimeRange = (start: string, end: string) => {
        try {
            const startDate = new Date(start);
            const endDate = new Date(end);
            return `${startDate.toLocaleTimeString()} - ${endDate.toLocaleTimeString()}`;
        } catch {
            return `${start} - ${end}`;
        }
    };

    const totalPages = history ? Math.ceil(history.total / pageSize) : 0;

    return (
        <DashboardLayout>
            <div className="space-y-8">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="space-y-1">
                        <h1 className="text-3xl font-semibold tracking-tight">Transparency</h1>
                        <p className="text-muted-foreground text-sm">
                            Cryptographic proof of API usage integrity
                        </p>
                    </div>
                    <Button
                        variant="outline"
                        onClick={() => {
                            fetchLatestRoot();
                            fetchHistory(currentPage);
                        }}
                        disabled={isLoadingLatest || isLoadingHistory}
                        className="gap-2"
                    >
                        <RefreshCw className={`h-4 w-4 ${(isLoadingLatest || isLoadingHistory) ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>

                {/* Error State */}
                {error && (
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {/* Latest Merkle Root */}
                <Card className="border-border/50 bg-card/50 backdrop-blur">
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                                    <Shield className="h-5 w-5 text-green-500" />
                                </div>
                                <div>
                                    <CardTitle>Latest Merkle Root</CardTitle>
                                    <CardDescription className="text-xs">
                                        Most recent cryptographic proof
                                    </CardDescription>
                                </div>
                            </div>
                            {latestRoot && (
                                <Badge variant="outline" className="gap-1.5">
                                    <Hash className="h-3 w-3" />
                                    Batch #{latestRoot.batch_id}
                                </Badge>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {isLoadingLatest ? (
                            <div className="space-y-3">
                                <Skeleton className="h-12 w-full" />
                                <Skeleton className="h-20 w-full" />
                            </div>
                        ) : latestRoot ? (
                            <>
                                {/* Merkle Root Display */}
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm font-medium text-muted-foreground">Merkle Root</span>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => copyToClipboard(latestRoot.merkle_root, latestRoot.batch_id)}
                                            className="h-8 px-2"
                                        >
                                            {copiedRoot === latestRoot.batch_id ? (
                                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                                            ) : (
                                                <Copy className="h-4 w-4" />
                                            )}
                                        </Button>
                                    </div>
                                    <div className="rounded-md border border-green-500/20 bg-green-500/5 px-4 py-3 font-mono text-sm break-all">
                                        {latestRoot.merkle_root}
                                    </div>
                                </div>

                                {/* Metadata */}
                                <div className="grid gap-4 md:grid-cols-3">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <Clock className="h-4 w-4" />
                                            <span>Time Range</span>
                                        </div>
                                        <p className="text-sm font-medium">
                                            {formatTimeRange(latestRoot.start_time, latestRoot.end_time)}
                                        </p>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <FileCheck2 className="h-4 w-4" />
                                            <span>Requests</span>
                                        </div>
                                        <p className="text-sm font-medium">{latestRoot.request_count} requests</p>
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <Shield className="h-4 w-4" />
                                            <span>Computed</span>
                                        </div>
                                        <p className="text-sm font-medium">{formatDate(latestRoot.created_at)}</p>
                                    </div>
                                </div>

                                {/* Verification Button */}
                                <div className="pt-2">
                                    <Button
                                        onClick={() => handleVerify(latestRoot.batch_id)}
                                        disabled={isVerifying}
                                        className="w-full gap-2"
                                    >
                                        {isVerifying ? (
                                            <>
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                                Verifying...
                                            </>
                                        ) : (
                                            <>
                                                <Shield className="h-4 w-4" />
                                                Verify Integrity
                                            </>
                                        )}
                                    </Button>
                                </div>

                                {/* Verification Result */}
                                {verificationResult && verificationResult.batchId === latestRoot.batch_id && (
                                    <Alert className={verificationResult.verified ? "border-green-500/50 bg-green-500/5" : "border-red-500/50 bg-red-500/5"}>
                                        {verificationResult.verified ? (
                                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                                        ) : (
                                            <AlertCircle className="h-4 w-4 text-red-500" />
                                        )}
                                        <AlertDescription className={verificationResult.verified ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                                            <div className="space-y-2">
                                                <p className="font-medium">
                                                    {verificationResult.verified
                                                        ? verificationResult.isBlockchain
                                                            ? "✓ Verified on Sepolia Blockchain!"
                                                            : "✓ Verified Locally (Not yet on blockchain)"
                                                        : "✗ Integrity check failed!"}
                                                </p>
                                                {verificationResult.verified && verificationResult.isBlockchain && (
                                                    <div className="text-xs space-y-1 pt-1">
                                                        <p>Block: #{verificationResult.blockNumber}</p>
                                                        <p className="font-mono break-all">Tx: {verificationResult.txHash}</p>
                                                        <a
                                                            href={verificationResult.etherscanUrl}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-green-600 dark:text-green-400 hover:underline inline-flex items-center gap-1"
                                                        >
                                                            View on Etherscan →
                                                        </a>
                                                    </div>
                                                )}
                                            </div>
                                        </AlertDescription>
                                    </Alert>
                                )}
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <Shield className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                                <p className="text-sm font-medium mb-1">No Merkle roots yet</p>
                                <p className="text-xs text-muted-foreground max-w-md">
                                    Make at least 10 requests through the gateway to generate the first Merkle root
                                </p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Historical Merkle Roots */}
                <Card className="border-border/50 bg-card/50 backdrop-blur">
                    <CardHeader>
                        <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                <FileCheck2 className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                                <CardTitle>Historical Merkle Roots</CardTitle>
                                <CardDescription className="text-xs">
                                    Previous cryptographic proofs
                                </CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {isLoadingHistory ? (
                            <div className="space-y-4">
                                <Skeleton className="h-10 w-full" />
                                <Skeleton className="h-32 w-full" />
                            </div>
                        ) : history && history.merkle_roots.length > 0 ? (
                            <>
                                <div className="rounded-md border border-border overflow-hidden">
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead className="w-[100px]">Batch ID</TableHead>
                                                <TableHead>Merkle Root</TableHead>
                                                <TableHead className="w-[150px]">Requests</TableHead>
                                                <TableHead className="w-[200px]">Created</TableHead>
                                                <TableHead className="w-[100px] text-right">Actions</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {history.merkle_roots.map((root) => (
                                                <TableRow key={root.batch_id}>
                                                    <TableCell className="font-medium">
                                                        <Badge variant="outline">#{root.batch_id}</Badge>
                                                    </TableCell>
                                                    <TableCell>
                                                        <code className="text-xs font-mono bg-muted px-2 py-1 rounded">
                                                            {root.merkle_root.substring(0, 16)}...{root.merkle_root.substring(48)}
                                                        </code>
                                                    </TableCell>
                                                    <TableCell>{root.request_count}</TableCell>
                                                    <TableCell className="text-sm text-muted-foreground">
                                                        {formatDate(root.created_at)}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => copyToClipboard(root.merkle_root, root.batch_id)}
                                                            className="h-8 px-2"
                                                        >
                                                            {copiedRoot === root.batch_id ? (
                                                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                                                            ) : (
                                                                <Copy className="h-4 w-4" />
                                                            )}
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                </div>

                                {/* Pagination */}
                                {totalPages > 1 && (
                                    <div className="flex items-center justify-between pt-4">
                                        <p className="text-sm text-muted-foreground">
                                            Showing {currentPage * pageSize + 1} to {Math.min((currentPage + 1) * pageSize, history.total)} of {history.total} roots
                                        </p>
                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => fetchHistory(currentPage - 1)}
                                                disabled={currentPage === 0 || isLoadingHistory}
                                                className="gap-2"
                                            >
                                                <ChevronLeft className="h-4 w-4" />
                                                Previous
                                            </Button>
                                            <span className="text-sm text-muted-foreground">
                                                Page {currentPage + 1} of {totalPages}
                                            </span>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => fetchHistory(currentPage + 1)}
                                                disabled={currentPage >= totalPages - 1 || isLoadingHistory}
                                                className="gap-2"
                                            >
                                                Next
                                                <ChevronRight className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <FileCheck2 className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
                                <p className="text-sm font-medium mb-1">No historical roots</p>
                                <p className="text-xs text-muted-foreground">
                                    Historical Merkle roots will appear here as batches are computed
                                </p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </DashboardLayout>
    );
}
