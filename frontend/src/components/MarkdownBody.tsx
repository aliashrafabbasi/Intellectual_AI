import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { markdownComponents } from "./markdownComponents";

type Props = {
  content: string;
  className?: string;
  /** Shown when content is empty (e.g. streaming start). */
  placeholder?: string;
};

export function MarkdownBody({ content, className, placeholder }: Props) {
  const text = content.trim();
  if (!text && placeholder) {
    return (
      <div className={className}>
        <span className="md-placeholder">{placeholder}</span>
      </div>
    );
  }
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
