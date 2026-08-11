import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

type ExportError = {
  taskId: string;
  action: string;
  error: string;
};

export type ExportSummary = {
  total: number;
  created: number;
  updated: number;
  failed: number;
  errors: ExportError[];
};

type Props = {
  projectId: string;
  canExport: boolean;
};

export function AirtableExport({ projectId, canExport }: Props) {
  const [summary, setSummary] = useState<ExportSummary | null>(null);
  const exportTasks = useMutation({
    mutationFn: () =>
      apiFetch<ExportSummary>(`/api/projects/${projectId}/export`, {
        method: "POST",
      }),
    onMutate: () => setSummary(null),
    onSuccess: setSummary,
  });

  if (!canExport) return null;

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={() => exportTasks.mutate()}
        disabled={exportTasks.isPending}
        className="text-sm px-4 py-2 rounded-md border border-border hover:border-accent disabled:opacity-50"
      >
        {exportTasks.isPending ? "exporting…" : "Export to Airtable"}
      </button>

      {exportTasks.isError && (
        <p className="text-sm text-red-400 max-w-md text-right" role="alert">
          {exportTasks.error instanceof Error
            ? exportTasks.error.message
            : "Airtable export failed"}
        </p>
      )}

      {summary && (
        <div
          className={`text-xs text-right ${summary.failed ? "text-amber-400" : "text-emerald-400"}`}
          role="status"
        >
          <p>
            {summary.failed
              ? "Export completed with failures."
              : "Export completed successfully."}
          </p>
          <p>
            total: {summary.total} · created: {summary.created} · updated:{" "}
            {summary.updated} · failed: {summary.failed}
          </p>
        </div>
      )}
    </div>
  );
}
