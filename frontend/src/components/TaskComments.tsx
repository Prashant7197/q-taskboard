import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { ApiComment } from "@/types";

type Props = {
  taskId: string;
  canPost: boolean;
};

export function TaskComments({ taskId, canPost }: Props) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");

  const commentsQuery = useQuery({
    queryKey: ["comments", taskId],
    queryFn: () =>
      apiFetch<{ comments: ApiComment[] }>(`/api/tasks/${taskId}/comments`),
  });

  const createComment = useMutation({
    mutationFn: (commentBody: string) =>
      apiFetch<{ comment: ApiComment }>(`/api/tasks/${taskId}/comments`, {
        method: "POST",
        body: JSON.stringify({ body: commentBody }),
      }),
    onSuccess: ({ comment }) => {
      queryClient.setQueryData<{ comments: ApiComment[] }>(
        ["comments", taskId],
        (current) => ({ comments: [...(current?.comments ?? []), comment] }),
      );
      setBody("");
    },
  });

  function submitComment(event: FormEvent) {
    event.preventDefault();
    const trimmedBody = body.trim();
    if (trimmedBody) createComment.mutate(trimmedBody);
  }

  return (
    <section className="border-t border-border mt-5 pt-5">
      <h3 className="text-sm font-medium mb-3">comments</h3>

      {commentsQuery.isLoading && (
        <p className="text-xs text-muted">loading comments…</p>
      )}
      {commentsQuery.isError && (
        <p className="text-sm text-red-400" role="alert">
          {commentsQuery.error instanceof Error
            ? commentsQuery.error.message
            : "failed to load comments"}
        </p>
      )}

      {commentsQuery.data && (
        <div className="space-y-3 mb-4">
          {commentsQuery.data.comments.length === 0 ? (
            <p className="text-xs text-muted">no comments yet</p>
          ) : (
            commentsQuery.data.comments.map((comment) => (
              <article key={comment.id} className="rounded-md bg-bg border border-border p-3">
                <div className="flex justify-between gap-3 text-xs text-muted mb-1">
                  <span>{comment.author.name}</span>
                  <time dateTime={comment.created_at}>
                    {new Date(comment.created_at).toLocaleString()}
                  </time>
                </div>
                <p className="text-sm whitespace-pre-wrap break-words">{comment.body}</p>
              </article>
            ))
          )}
        </div>
      )}

      {canPost && (
        <form onSubmit={submitComment} className="space-y-2">
          <label className="block">
            <span className="sr-only">comment</span>
            <textarea
              value={body}
              onChange={(event) => setBody(event.target.value)}
              placeholder="add a comment"
              rows={3}
              className="block w-full rounded-md bg-bg border border-border px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </label>
          {createComment.isError && (
            <p className="text-sm text-red-400" role="alert">
              {createComment.error instanceof Error
                ? createComment.error.message
                : "failed to post comment"}
            </p>
          )}
          <button
            type="submit"
            disabled={!body.trim() || createComment.isPending}
            className="text-sm px-4 py-2 rounded-md bg-accent text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {createComment.isPending ? "posting…" : "post comment"}
          </button>
        </form>
      )}
    </section>
  );
}
