import { useCallback, useMemo, useRef } from "react";
import type { EditorState } from "lexical";
import { LexicalComposer } from "@lexical/react/LexicalComposer";
import { RichTextPlugin } from "@lexical/react/LexicalRichTextPlugin";
import { ContentEditable } from "@lexical/react/LexicalContentEditable";
import { HistoryPlugin } from "@lexical/react/LexicalHistoryPlugin";
import { OnChangePlugin } from "@lexical/react/LexicalOnChangePlugin";
import { MarkdownShortcutPlugin } from "@lexical/react/LexicalMarkdownShortcutPlugin";
import { ListPlugin } from "@lexical/react/LexicalListPlugin";
import { LinkPlugin } from "@lexical/react/LexicalLinkPlugin";
import { LexicalErrorBoundary } from "@lexical/react/LexicalErrorBoundary";
import { CodeNode, CodeHighlightNode } from "@lexical/code";
import { ListItemNode, ListNode } from "@lexical/list";
import { HeadingNode, QuoteNode } from "@lexical/rich-text";
import { LinkNode } from "@lexical/link";
import { clsx } from "clsx";
import {
  $convertFromMarkdownString,
  $convertToMarkdownString,
  TRANSFORMERS
} from "@lexical/markdown";
import { useLexicalComposerContext } from "@lexical/react/LexicalComposerContext";
import { useEffect } from "react";

type MarkdownLexicalEditorProps = {
  value: string;
  onChange: (nextMarkdown: string) => void;
  placeholder?: string;
  className?: string;
  containerClassName?: string;
  contentEditableClassName?: string;
};

const theme = {
  paragraph: "mb-3 leading-relaxed text-slate-800 dark:text-slate-200",
  heading: {
    h1: "text-2xl font-semibold text-slate-900 dark:text-white mb-4 leading-tight",
    h2: "text-xl font-semibold text-slate-900 dark:text-white mb-3",
    h3: "text-lg font-semibold text-slate-800 dark:text-slate-100 mb-2"
  },
  quote: "border-l-4 border-purple-200 dark:border-purple-500/60 pl-4 italic text-slate-600 dark:text-slate-300",
  list: {
    nested: {
      listitem: "list-disc list-inside"
    },
    ol: "list-decimal list-outside ml-6 space-y-2 text-slate-800 dark:text-slate-200",
    ul: "list-disc list-outside ml-6 space-y-2 text-slate-800 dark:text-slate-200"
  },
  listitem: "text-slate-800 dark:text-slate-200",
  code: "font-mono text-sm bg-slate-950/90 text-lime-100 rounded-lg px-4 py-3 overflow-x-auto",
  text: {
    bold: "font-semibold",
    italic: "italic",
    underline: "underline",
    strikethrough: "line-through",
    code: "font-mono text-sm bg-slate-200/70 dark:bg-slate-800/70 px-1.5 py-0.5 rounded"
  }
};

function MarkdownInitialiser({ markdown }: { markdown: string }) {
  const [editor] = useLexicalComposerContext();
  const hasInitialised = useRef(false);

  useEffect(() => {
    if (hasInitialised.current) {
      return;
    }
    hasInitialised.current = true;
    editor.update(() => {
      $convertFromMarkdownString(markdown || "", TRANSFORMERS);
    });
  }, [editor, markdown]);

  return null;
}

function MarkdownOnChange({ onChange }: { onChange: (markdown: string) => void }) {
  const handleChange = useCallback(
    (editorState: EditorState) => {
      editorState.read(() => {
        const markdown = $convertToMarkdownString(TRANSFORMERS);
        onChange(markdown);
      });
    },
    [onChange]
  );

  return <OnChangePlugin onChange={handleChange} />;
}

function Placeholder({ placeholder }: { placeholder?: string }) {
  if (!placeholder) {
    return null;
  }
  return (
    <div className="pointer-events-none absolute inset-x-6 top-6 text-base text-slate-400 dark:text-slate-500">
      {placeholder}
    </div>
  );
}

export function MarkdownLexicalEditor({
  value,
  onChange,
  placeholder,
  className = "",
  containerClassName = "",
  contentEditableClassName = ""
}: MarkdownLexicalEditorProps) {
  const initialConfig = useMemo(
    () => ({
      namespace: "agent-config-markdown",
      theme,
      nodes: [
        HeadingNode,
        QuoteNode,
        ListNode,
        ListItemNode,
        CodeNode,
        CodeHighlightNode,
        LinkNode
      ],
      onError(error: Error) {
        console.error("Lexical error:", error);
        throw error;
      }
    }),
    []
  );

  return (
    <div className={clsx("relative", className)}>
      <LexicalComposer initialConfig={initialConfig}>
        <MarkdownInitialiser markdown={value} />
        <div
          className={clsx(
            "relative min-h-[520px] rounded-xl border border-slate-200 bg-white shadow-inner dark:border-slate-700 dark:bg-slate-900",
            containerClassName
          )}
        >
          <RichTextPlugin
            contentEditable=
              {(
                <ContentEditable
                  className={clsx(
                    "relative mx-6 my-6 min-h-[420px] whitespace-pre-wrap text-base leading-relaxed text-slate-900 focus:outline-none dark:text-slate-100",
                    contentEditableClassName
                  )}
                />
              )}
            placeholder={<Placeholder placeholder={placeholder} />}
            ErrorBoundary={LexicalErrorBoundary}
          />
          <HistoryPlugin />
          <ListPlugin />
          <LinkPlugin />
          <MarkdownShortcutPlugin transformers={TRANSFORMERS} />
          <MarkdownOnChange onChange={onChange} />
        </div>
      </LexicalComposer>
    </div>
  );
}
