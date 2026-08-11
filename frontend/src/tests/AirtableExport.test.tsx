import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AirtableExport } from "@/components/AirtableExport";

function jsonResponse(data: unknown, ok = true) {
  return {
    ok,
    status: ok ? 200 : 500,
    text: async () => JSON.stringify(data),
  };
}

function renderExport(canExport = true) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AirtableExport projectId="p_1" canExport={canExport} />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("<AirtableExport />", () => {
  it("is hidden for a role that cannot export", () => {
    renderExport(false);
    expect(screen.queryByRole("button", { name: "Export to Airtable" })).not.toBeInTheDocument();
  });

  it("disables repeated clicks while exporting and shows a successful summary", async () => {
    let resolveRequest!: (value: ReturnType<typeof jsonResponse>) => void;
    const pending = new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
      resolveRequest = resolve;
    });
    const fetchMock = vi.fn().mockReturnValue(pending);
    vi.stubGlobal("fetch", fetchMock);
    renderExport();

    fireEvent.click(screen.getByRole("button", { name: "Export to Airtable" }));
    const pendingButton = await screen.findByRole("button", { name: "exporting…" });
    expect(pendingButton).toBeDisabled();
    fireEvent.click(pendingButton);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    resolveRequest(jsonResponse({
      total: 10, created: 8, updated: 2, failed: 0, errors: [],
    }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "total: 10 · created: 8 · updated: 2 · failed: 0",
    );
    expect(fetchMock.mock.calls[0][0]).toBe("/api/projects/p_1/export");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });
  });

  it("clearly reports a partially successful export", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({
        total: 10,
        created: 7,
        updated: 1,
        failed: 2,
        errors: [{ taskId: "t_1", action: "created", error: "invalid record" }],
      })),
    );
    renderExport();

    fireEvent.click(screen.getByRole("button", { name: "Export to Airtable" }));

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("Export completed with failures.");
    expect(status).toHaveTextContent("failed: 2");
  });

  it("shows the endpoint error message when export fails completely", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ error: "Airtable unavailable" }, false)),
    );
    renderExport();

    fireEvent.click(screen.getByRole("button", { name: "Export to Airtable" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Airtable unavailable");
  });
});
