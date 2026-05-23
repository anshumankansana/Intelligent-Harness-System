"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
  filename?: string;
};

export function MemoryDocument({ content, filename }: Props) {
  return (
    <div className="memory-doc panel max-w-3xl p-8">
      {filename && (
        <p className="mb-6 font-mono text-[10px] uppercase tracking-widest text-harness-muted">
          {filename}
        </p>
      )}
      <article className="memory-prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </article>
    </div>
  );
}
