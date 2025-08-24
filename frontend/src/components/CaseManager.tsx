import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ContextCase {
    case_id: string;
    case_type: string;
    status: "open" | "in_progress" | "pending" | "closed" | "escalated" | "resolved";
    priority: "low" | "medium" | "high" | "urgent";
    extracted_data: Record<string, unknown>;
    last_updated: string;
    confidence_score: number;
    message_count: number;
    created_by_ai: boolean;
    manual_override: boolean;
    source_channel: string;
    assigned_agent?: string;
}

export const CaseManager: React.FC<{ workspaceId: string }> = ({ workspaceId }) => {
    const [cases, setCases] = useState<ContextCase[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedCase, setSelectedCase] = useState<ContextCase | null>(null);
    const [activeTab, setActiveTab] = useState("open");

    useEffect(() => {
        fetchCases();
    }, [workspaceId, activeTab]);

    const fetchCases = async () => {
        try {
            const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
            const response = await fetch(`${API_BASE_URL}/api/v1/context/workspaces/${workspaceId}/cases/?status=${activeTab}`);
            const data = await response.json();
            setCases(data.results || data.cases || []);
        } catch (error) {
            console.error("Failed to fetch cases:", error);
        } finally {
            setLoading(false);
        }
    };

    const updateCaseStatus = async (caseId: string, newStatus: string) => {
        try {
            const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
            await fetch(`${API_BASE_URL}/api/v1/context/workspaces/${workspaceId}/cases/${caseId}/`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: newStatus, manual_override: true })
            });
            fetchCases();
        } catch (error) {
            console.error("Failed to update case status:", error);
        }
    };

    const renderCaseCard = (case_item: ContextCase) => (
        <Card key={case_item.case_id} className="mb-4 cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-lg">{case_item.case_id}</CardTitle>
                        <p className="text-sm text-gray-600 capitalize">{case_item.case_type} Case</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                        <Badge variant={case_item.status === "open" ? "default" : "secondary"}>
                            {case_item.status.replace("_", " ")}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                            Confidence: {Math.round(case_item.confidence_score * 100)}%
                        </Badge>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-2">
                    {/* Dynamic Data Display */}
                    {Object.entries(case_item.extracted_data).slice(0, 3).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                            <span className="font-medium capitalize">{key.replace("_", " ")}:</span>
                            <span className="text-gray-600 truncate max-w-48">
                                {typeof value === "object" ? JSON.stringify(value) : String(value)}
                            </span>
                        </div>
                    ))}
                    
                    <div className="flex justify-between items-center mt-4 pt-2 border-t">
                        <div className="text-xs text-gray-500">
                            {case_item.message_count} messages • Updated {new Date(case_item.last_updated).toLocaleDateString()}
                        </div>
                        <div className="flex gap-2">
                            {case_item.status === "open" && (
                                <Button size="sm" variant="outline" onClick={() => updateCaseStatus(case_item.case_id, "closed")}>
                                    Close Case
                                </Button>
                            )}
                            <Button size="sm" variant="ghost" onClick={() => setSelectedCase(case_item)}>
                                View Details
                            </Button>
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold">Context Cases</h2>
                <div className="text-sm text-gray-600">
                    Total: {cases.length} cases
                </div>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="open">Open ({cases.filter(c => c.status === "open").length})</TabsTrigger>
                    <TabsTrigger value="in_progress">In Progress</TabsTrigger>
                    <TabsTrigger value="pending">Pending</TabsTrigger>
                    <TabsTrigger value="closed">Closed</TabsTrigger>
                </TabsList>

                <TabsContent value={activeTab} className="mt-6">
                    {loading ? (
                        <div className="flex justify-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : cases.length === 0 ? (
                        <Card>
                            <CardContent className="flex flex-col items-center justify-center py-8">
                                <p className="text-gray-500">No {activeTab} cases found</p>
                                <p className="text-sm text-gray-400 mt-2">
                                    Cases will appear here as your AI agent analyzes conversations
                                </p>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid gap-4">
                            {cases.map(renderCaseCard)}
                        </div>
                    )}
                </TabsContent>
            </Tabs>

            {/* Case Details Modal */}
            {selectedCase && (
                <CaseDetailModal 
                    case_item={selectedCase} 
                    onClose={() => setSelectedCase(null)}
                    onUpdate={fetchCases}
                />
            )}
        </div>
    );
};

// Case Detail Modal Component
const CaseDetailModal: React.FC<{
    case_item: ContextCase;
    onClose: () => void;
    onUpdate: () => void;
}> = ({ case_item, onClose, onUpdate }) => {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="text-xl font-bold">{case_item.case_id}</h3>
                        <p className="text-gray-600 capitalize">{case_item.case_type} Case Details</p>
                    </div>
                    <Button variant="ghost" onClick={onClose}>×</Button>
                </div>

                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-sm font-medium text-gray-700">Status</label>
                            <Badge className="ml-2">{case_item.status.replace("_", " ")}</Badge>
                        </div>
                        <div>
                            <label className="text-sm font-medium text-gray-700">Confidence</label>
                            <span className="ml-2">{Math.round(case_item.confidence_score * 100)}%</span>
                        </div>
                    </div>

                    <div>
                        <label className="text-sm font-medium text-gray-700 block mb-2">Extracted Data</label>
                        <div className="bg-gray-50 rounded-lg p-4">
                            <pre className="text-sm overflow-x-auto">
                                {JSON.stringify(case_item.extracted_data, null, 2)}
                            </pre>
                        </div>
                    </div>

                    <div className="flex gap-2 pt-4 border-t">
                        <Button variant="outline" onClick={onClose}>Close</Button>
                        {case_item.status !== "closed" && (
                            <Button onClick={() => {
                                // Update case status and refresh
                                onUpdate();
                                onClose();
                            }}>
                                Mark as Closed
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
