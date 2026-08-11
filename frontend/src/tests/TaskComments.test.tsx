import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TaskComments } from "@/components/TaskComments";

const existingComment = {
  id: "c_1",
  body: "Initial update",
  author: { id: "u_1", name: "Meera Iyer", email: "meera@taskboard.dev" },
  created_at: "2026-08-11T10:00:00Z",
};

function jsonResponse(data: unknown, ok = true) {
  return {
    ok,
    status: ok ? 200 : 500,
    text: async () => JSON.stringify(data),
  };
}

function renderComments(canPost: boolean) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TaskComments taskId="t_1" canPost={canPost} />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("<TaskComments />", () => {
  it("shows loading then renders comments for a viewer without a post form", async () => {
    let resolveRequest!: (value: ReturnType<typeof jsonResponse>) => void;
    const pending = new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
      resolveRequest = resolve;
    });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));

    renderComments(false);
    expect(screen.getByText("loading comments…")).toBeInTheDocument();

    resolveRequest(jsonResponse({ comments: [existingComment] }));
    expect(await screen.findByText("Initial update")).toBeInTheDocument();
    expect(screen.getByText("Meera Iyer")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "post comment" })).not.toBeInTheDocument();
  });

  it("allows a member to post and immediately displays the new comment", async () => {
    const postedComment = {
      ...existingComment,
      id: "c_2",
      body: "Fresh update",
      created_at: "2026-08-11T11:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ comments: [existingComment] }))
      .mockResolvedValueOnce(jsonResponse({ comment: postedComment }));
    vi.stubGlobal("fetch", fetchMock);

    renderComments(true);
    await screen.findByText("Initial update");
    fireEvent.change(screen.getByPlaceholderText("add a comment"), {
      target: { value: "Fresh update" },
    });
    fireEvent.click(screen.getByRole("button", { name: "post comment" }));

    expect(await screen.findByText("Fresh update")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1][0]).toBe("/api/tasks/t_1/comments");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ body: "Fresh update" }),
    });
  });

  it("shows a useful API error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ error: "comments unavailable" }, false)),
    );

    renderComments(true);

    expect(await screen.findByRole("alert")).toHaveTextContent("comments unavailable");
  });
});
