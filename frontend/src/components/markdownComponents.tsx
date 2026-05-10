import React, { useCallback, useState } from "react";
import type { Components } from "react-markdown";

function nodeToPlainText(node: React.ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeToPlainText).join("");
  if (React.isValidElement(node)) {
    return nodeToPlainText(node.props.children as React.ReactNode);
  }
  return "";
}

function PreWithToolbar({ children }: React.HTMLAttributes<HTMLPreElement>) {
  const rawText = nodeToPlainText(children);

  let langLabel = "text";
  try {
    const child = React.Children.only(children) as React.ReactElement<{ className?: string }>;
    const cls = child.props.className ?? "";
    const langMatch = /language-([\w+-]+)/.exec(cls);
    if (langMatch) langLabel = langMatch[1];
  } catch {
    /* not a single code child */
  }

  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(rawText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [rawText]);

  return (
    <div className="md-code-panel">
      <div className="md-code-toolbar">
        <span className="md-code-lang">{langLabel}</span>
        <button type="button" className="md-code-copy-btn" onClick={() => void handleCopy()}>
          {copied ? "Copied!" : "Copy code"}
        </button>
      </div>
      <pre className="md-code-pre">{children}</pre>
    </div>
  );
}

function CodeElement({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLElement> & { node?: unknown }) {
  const isFence = typeof className === "string" && className.includes("language-");
  const rest = { ...props } as Record<string, unknown>;
  delete rest.node;

  if (isFence) {
    return (
      <code className={className} {...(rest as React.HTMLAttributes<HTMLElement>)}>
        {children}
      </code>
    );
  }
  const inlineClass = ["md-inline-code", className].filter(Boolean).join(" ");
  return (
    <code className={inlineClass} {...(rest as React.HTMLAttributes<HTMLElement>)}>
      {children}
    </code>
  );
}

function openInNewTab(href: string | undefined): boolean {
  if (!href || href.startsWith("#")) return false;
  try {
    const u = new URL(href, window.location.origin);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

function MarkdownLink({
  href,
  children,
  ...props
}: React.AnchorHTMLAttributes<HTMLAnchorElement> & { node?: unknown }) {
  const rest = { ...props } as Record<string, unknown>;
  delete rest.node;
  const external = openInNewTab(typeof href === "string" ? href : undefined);
  return (
    <a
      href={href}
      {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {children}
    </a>
  );
}

export const markdownComponents: Partial<Components> = {
  pre: PreWithToolbar,
  code: CodeElement,
  a: MarkdownLink,
};
