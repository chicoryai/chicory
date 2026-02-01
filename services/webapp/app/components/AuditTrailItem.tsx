import React, { useEffect, useMemo, useState } from "react";
import { ChevronDownIcon, ChevronRightIcon, CheckCircleIcon, XCircleIcon, WrenchIcon, SparklesIcon } from "@heroicons/react/24/outline";
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";
import { MarkdownRenderer } from "~/components/MarkdownRenderer";
import type {
  TrailItem,
  SystemMessageData,
  AssistantMessageData,
  UserMessageData,
  ResultMessageData,
  DictMessageData,
  ToolUseBlock,
  ToolResultBlock,
  AssistantMessageBlock,
  ThinkingBlock
} from "~/types/auditTrail";
import { extractAssistantBlocks, extractToolResultBlocks, parseStructuredData, shouldDisplayTrailItem } from "~/types/auditTrail";

type Structured = SystemMessageData | AssistantMessageData | UserMessageData | ResultMessageData | DictMessageData | Record<string, unknown> | null;

interface AuditTrailItemProps {
  item: TrailItem;
  toolResults?: Map<string, ToolResultBlock>;
}

const AuditTrailItem: React.FC<AuditTrailItemProps> = ({ item, toolResults }) => {
  const [isSystemExpanded, setIsSystemExpanded] = useState(false);
  const [expandedToolInputs, setExpandedToolInputs] = useState<Record<string, boolean>>({});
  const [expandedToolOutputs, setExpandedToolOutputs] = useState<Record<string, boolean>>({});
  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setIsSystemExpanded(false);
    setExpandedToolInputs({});
    setExpandedToolOutputs({});
    setExpandedThinking({});
  }, [item.id, item.message_id]);

  const structured = useMemo<Structured>(() => parseStructuredData(item.structured_data), [item.structured_data]);

  const hasType = (value: Structured): value is SystemMessageData | AssistantMessageData | UserMessageData | ResultMessageData =>
    Boolean(value) && typeof value === "object" && value !== null && "type" in value && typeof (value as any).type === "string";

  const hasRole = (value: Structured): value is DictMessageData =>
    Boolean(value) && typeof value === "object" && value !== null && "role" in value && typeof (value as any).role === "string";

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      fractionalSecondDigits: 3
    });
  };

  const renderSystemMessage = (data: SystemMessageData) => (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm text-blue-500">
        <span className="font-medium">System Initialized</span>
        <button
          onClick={() => setIsSystemExpanded(prev => !prev)}
          className="rounded p-0.5 text-blue-300 hover:bg-blue-100/30 hover:text-blue-600"
        >
          {isSystemExpanded ? <ChevronDownIcon className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
        </button>
      </div>
      {isSystemExpanded && (
        <div className="space-y-1 rounded bg-blue-50 p-3 text-xs text-blue-900 dark:bg-blue-900/30 dark:text-blue-100">
          <div>Model: {data.content?.data?.model ?? "unknown"}</div>
          <div>Session: {data.content?.data?.session_id ?? "unknown"}</div>
          <div>Tools: {data.content?.data?.tools?.length ?? 0} available</div>
        </div>
      )}
    </div>
  );

  const normalizeType = (value: unknown): string =>
    typeof value === "string" ? value.toLowerCase() : "";

  const extractBlockText = (block: AssistantMessageBlock): string | null => {
    if (!block || typeof block !== "object") return null;

    if (typeof (block as any).text === "string") {
      return (block as any).text;
    }

    const blockType = normalizeType((block as any).type);

    if (blockType.includes("text") && typeof (block as any).content === "string") {
      return (block as any).content as string;
    }

    if (blockType.includes("text") && Array.isArray((block as any).content)) {
      return (block as any).content
        .map((node: any) => {
          if (typeof node === "string") return node;
          if (node && typeof node === "object" && typeof node.text === "string") {
            return node.text;
          }
          return "";
        })
        .filter(Boolean)
        .join("\n");
    }

    if (blockType === "thinking" && typeof (block as any).thinking === "string") {
      return (block as any).thinking as string;
    }

    return null;
  };

  const isToolUseBlockLike = (block: AssistantMessageBlock): block is ToolUseBlock => {
    if (!block || typeof block !== "object") return false;
    const blockType = normalizeType((block as any).type);
    if (blockType === "tooluseblock" || blockType === "tool_use_block" || blockType === "tool_use") {
      return true;
    }
    return typeof (block as any).name === "string" && typeof (block as any).input === "object" && (block as any).input !== null;
  };

  const isThinkingBlock = (block: AssistantMessageBlock): block is ThinkingBlock => {
    if (!block || typeof block !== "object") return false;
    const blockType = normalizeType((block as any).type);
    return (blockType === "thinkingblock" || blockType === "thinking") && typeof (block as any).thinking === "string";
  };

  const assistantBlocks = useMemo(() => {
    if (!structured || !hasType(structured) || structured.type !== "AssistantMessage") {
      return [] as AssistantMessageBlock[];
    }
    return extractAssistantBlocks(structured);
  }, [structured]);

  const assistantHasText = useMemo(
    () =>
      assistantBlocks.some(block => {
        if (isToolUseBlockLike(block) || isThinkingBlock(block)) return false;
        const text = extractBlockText(block);
        return Boolean(text && text.trim().length > 0);
      }),
    [assistantBlocks]
  );

  const assistantHasTool = useMemo(() => assistantBlocks.some(isToolUseBlockLike), [assistantBlocks]);

  const isToolOnlyAssistant = item.message_type === "AssistantMessage" && assistantHasTool && !assistantHasText;
  const showTimelineLine = item.message_type === "AssistantMessage" && !isToolOnlyAssistant;

  const renderAssistantMessage = (data: AssistantMessageData) => {
    const blocks = extractAssistantBlocks(data);

    if (!Array.isArray(blocks) || blocks.length === 0) {
      return (
        <div className="text-sm text-gray-500">
          <em>No assistant message content</em>
        </div>
      );
    }

    type Section = {
      text: string | null;
      tools: AssistantMessageBlock[];
      thinking: AssistantMessageBlock[];
    };

    const sections: Section[] = [];
    let currentSection: Section | null = null;

    blocks.forEach(block => {
      if (isThinkingBlock(block)) {
        if (!currentSection) {
          currentSection = { text: null, tools: [], thinking: [] };
          sections.push(currentSection);
        }
        currentSection.thinking.push(block);
        return;
      }

      if (isToolUseBlockLike(block)) {
        if (!currentSection) {
          currentSection = { text: null, tools: [], thinking: [] };
          sections.push(currentSection);
        }
        currentSection.tools.push(block);
        return;
      }

      const text = extractBlockText(block);
      if (text && text.trim().length > 0) {
        currentSection = { text, tools: [], thinking: [] };
        sections.push(currentSection);
      }
    });

    if (sections.length === 0) {
      // Handle case where only tools or thinking were present without preceding text
      const toolOnly = blocks.filter(isToolUseBlockLike);
      const thinkingOnly = blocks.filter(isThinkingBlock);
      if (toolOnly.length > 0 || thinkingOnly.length > 0) {
        sections.push({ text: null, tools: toolOnly, thinking: thinkingOnly });
      }
    }

    const hasRenderableContent = sections.some(section => section.text || section.tools.length > 0 || section.thinking.length > 0);

    if (!hasRenderableContent) {
      return (
        <div className="text-xs text-gray-500">
          <em>Unsupported assistant message content</em>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {sections.map((section, sectionIdx) => {
          const sectionKey = `section-${sectionIdx}`;
          return (
            <div key={sectionKey} className="space-y-2">
              {section.thinking.length > 0 && (
                <div className="space-y-2">
                  {section.thinking.map((thinkingBlock, thinkingIdx) => {
                    const thinkingId = `thinking-${sectionIdx}-${thinkingIdx}`;
                    const isExpanded = expandedThinking[thinkingId] ?? false;
                    const thinkingContent = (thinkingBlock as ThinkingBlock).thinking;
                    const shouldShowToggle = thinkingContent.length > 240;
                    const displayContent = isExpanded || !shouldShowToggle
                      ? thinkingContent
                      : thinkingContent.slice(0, 240) + (thinkingContent.length > 240 ? "…" : "");

                    const toggleThinking = () => {
                      setExpandedThinking(prev => ({
                        ...prev,
                        [thinkingId]: !isExpanded
                      }));
                    };

                    return (
                      <div key={thinkingId} className="space-y-2 rounded-lg bg-purple-50 p-3 dark:bg-purple-500/10 border border-purple-200 dark:border-purple-700">
                        <div className="flex items-center gap-2">
                          <SparklesIcon className="h-4 w-4 text-purple-500 dark:text-purple-300" />
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-purple-500 dark:text-purple-300 font-ui">
                            Thinking
                          </p>
                          <button
                            onClick={toggleThinking}
                            className="ml-auto rounded p-0.5 text-purple-400 hover:bg-purple-100/30 hover:text-purple-600 dark:hover:bg-purple-500/20"
                            aria-label={isExpanded ? "Collapse thinking" : "Expand thinking"}
                          >
                            {isExpanded ? <ChevronDownIcon className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
                          </button>
                        </div>
                        {isExpanded && (
                          <div className="space-y-1">
                            <div className="rounded-xl border border-purple-200 bg-white px-3 py-2 shadow-sm dark:border-purple-700 dark:bg-slate-900/60">
                              <pre className="whitespace-pre-wrap text-xs text-slate-700 dark:text-slate-200 font-body">
                                {displayContent}
                              </pre>
                            </div>
                            {shouldShowToggle && (
                              <button
                                onClick={toggleThinking}
                                className="text-xs font-medium text-purple-600 hover:text-purple-700 dark:text-purple-300"
                              >
                                {isExpanded ? 'Show less' : 'Show more'}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {section.text && (
                <MarkdownRenderer
                  content={section.text}
                  variant="task"
                  className="prose prose-sm max-w-none text-gray-900 dark:text-gray-100"
                />
              )}

              {section.tools.length > 0 && (
                <div className="space-y-3 rounded-lg bg-whitePurple-50 p-3 dark:bg-purple-500/10">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-purple-500 dark:text-purple-300">
                    Tool Use
                  </p>
                  {section.tools.map((tool, idx) => {
                    const normalized = tool as ToolUseBlock & { tool_use_id?: string };
                    const toolId = normalized.id ?? normalized.tool_use_id ?? `tool-${sectionIdx}-${idx}`;
                    const toolResult = toolResults?.get(toolId);
                    const inputExpanded = expandedToolInputs[toolId] ?? false;
                    const outputExpanded = expandedToolOutputs[toolId] ?? false;

                    const toggleInput = () => {
                      setExpandedToolInputs(prev => ({
                        ...prev,
                        [toolId]: !inputExpanded
                      }));
                    };

                    const toggleOutput = () => {
                      setExpandedToolOutputs(prev => ({
                        ...prev,
                        [toolId]: !outputExpanded
                      }));
                    };

                    let resultText = "";
                    if (toolResult) {
                      const content = toolResult.content;
                      if (typeof content === "string") {
                        resultText = content;
                      } else if (Array.isArray(content)) {
                        resultText = JSON.stringify(content[0] ?? content, null, 2);
                      } else if (content && typeof content === "object") {
                        resultText = JSON.stringify(content, null, 2);
                      }
                    }

                    const shouldShowToggle = resultText.length > 240;
                    const displayResult = outputExpanded || !shouldShowToggle
                      ? resultText
                      : resultText.slice(0, 240) + (resultText.length > 240 ? "…" : "");

                    return (
                      <div key={toolId} className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-purple-700 dark:text-purple-200">{normalized.name ?? "Tool"}</span>
                          <button
                            onClick={toggleInput}
                            className="rounded border border-purple-200 px-2 py-0.5 text-xs text-purple-500 hover:border-purple-400 hover:text-purple-600 dark:border-purple-400/50 dark:text-purple-200"
                          >
                            {inputExpanded ? "Hide input" : "View input"}
                          </button>
                        </div>
                        {toolResult && (
                          <div className="flex items-center gap-2 text-xs font-medium">
                            <span
                              className={`rounded-full px-2 py-0.5 ${toolResult.is_error ? 'bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-200' : 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-200'}`}
                            >
                              {toolResult.is_error ? 'Failed' : 'Succeeded'}
                            </span>
                            <span className="text-gray-500 dark:text-gray-400">{toolId.slice(0, 8)}…</span>
                          </div>
                        )}
                        {inputExpanded && (
                          <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-200">
                            <pre className="whitespace-pre-wrap">{JSON.stringify(normalized.input ?? null, null, 2)}</pre>
                          </div>
                        )}
                        {resultText && (
                          <div className="space-y-1">
                            <pre className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
                              {displayResult}
                            </pre>
                            {shouldShowToggle && (
                              <button
                                onClick={toggleOutput}
                                className="text-xs font-medium text-purple-600 hover:text-purple-700 dark:text-purple-300"
                              >
                                {outputExpanded ? 'Show less' : 'Show more'}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const renderUserMessage = (data: UserMessageData) => {
    const results = extractToolResultBlocks(data);
    if (!Array.isArray(results) || results.length === 0) {
      return (
        <div className="text-sm text-gray-500">
          <em>No tool results recorded</em>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {results.map((result, idx) => {
          const toolId = typeof result.tool_use_id === "string" ? result.tool_use_id : "unknown";
          return (
            <div key={`result-${idx}`} className="space-y-1">
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-300">
                {result.is_error ? (
                  <XCircleIcon className="h-3 w-3 text-rose-400" />
                ) : (
                  <CheckCircleIcon className="h-3 w-3 text-emerald-400" />
                )}
                <span>Tool result for {toolId.slice(0, 8)}…</span>
              </div>
              {typeof result.content === "string" && result.content && (
                <pre className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
                  {result.content.length > 240 ? `${result.content.slice(0, 240)}…` : result.content}
                </pre>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const renderResultMessage = (data: ResultMessageData) => {
    const raw = ((data as any)?.content && typeof (data as any).content === "object")
      ? (data as any).content as Record<string, unknown>
      : (data as unknown as Record<string, unknown>);

    if (!raw || typeof raw !== "object") {
      return (
        <div className="text-xs text-gray-500">
          <em>No result details available</em>
        </div>
      );
    }

    const rawAny = raw as Record<string, unknown>;

    const subtype = typeof rawAny.subtype === "string" ? (rawAny.subtype as string).toLowerCase() : undefined;
    const isError = typeof rawAny.is_error === "boolean"
      ? (rawAny.is_error as boolean)
      : subtype === "failed" || subtype === "error";

    const statusLabel = isError ? "Execution Failed" : "Execution Succeeded";

    const durationSeconds = (() => {
      const rawDuration = rawAny.duration_ms as unknown;
      const durationMs = typeof rawDuration === "number"
        ? rawDuration
        : typeof rawDuration === "string"
          ? Number(rawDuration)
          : NaN;

      if (!Number.isFinite(durationMs)) {
        return null;
      }

      const seconds = durationMs / 1000;
      return seconds >= 10 ? seconds.toFixed(1) : seconds.toFixed(2);
    })();

    return (
      <div className="flex items-center justify-between rounded-xl bg-white px-4 py-3 text-sm text-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
        <span className={isError ? "text-rose-500 dark:text-rose-300" : "text-emerald-500 dark:text-emerald-300"}>
          {statusLabel}
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-300">
          {durationSeconds != null ? `${durationSeconds} s` : "—"}
        </span>
      </div>
    );
  };

  const renderFallback = (data: DictMessageData | Record<string, unknown> | null) => (
    <div className="text-xs text-gray-500">
      <pre className="whitespace-pre-wrap">
        {data && typeof data === "object" ? JSON.stringify(data, null, 2) : "Unsupported trail entry"}
      </pre>
    </div>
  );

  const renderContent = () => {
    if (structured == null) {
      return renderFallback(null);
    }

    if (hasType(structured)) {
      switch (structured.type) {
        case "SystemMessage":
          return renderSystemMessage(structured);
        case "AssistantMessage":
          return renderAssistantMessage(structured);
        case "UserMessage":
          return renderUserMessage(structured);
        case "ResultMessage":
          return renderResultMessage(structured);
        default:
          return renderFallback(structured);
      }
    }

    if (hasRole(structured)) {
      return (
        <div className="text-sm text-gray-700 whitespace-pre-wrap dark:text-gray-200">
          {structured.content?.raw_content ?? "Raw content unavailable"}
        </div>
      );
    }

    return renderFallback(structured);
  };

  const renderIcon = () => {
    if (structured == null) {
      return <div className="h-2 w-2 rounded-full bg-gray-400" />;
    }
    if (hasType(structured)) {
      switch (structured.type) {
        case "SystemMessage":
          return <div className="h-2 w-2 rounded-full bg-blue-500" />;
        case "AssistantMessage":
          if (structured.content?.[0]?.type === "ToolUseBlock") {
            if (structured.content?.[0]?.name.includes("mcp")) {
              return <MCPGatewayIcon size={16} className="flex-grow-0" />;
            }
            return <WrenchIcon className="h-4 w-4" />;
          } else if (structured.content?.[0]?.type === "TextBlock") {
            return <div className="h-2 w-2 mr-1 rounded-full bg-purple-500" />;
          }
        case "UserMessage":
          return <div className="h-2 w-2 rounded-full bg-gray-500" />;
        case "ResultMessage":
          return structured.content?.is_error ? (
            <XCircleIcon className="h-4 w-4 text-red-500" />
          ) : (
            <CheckCircleIcon className="h-4 w-4 text-green-500" />
          );
        default:
          return <div className="h-2 w-2 rounded-full bg-gray-400" />;
      }
    }
    if (hasRole(structured)) {
      return structured.role === "assistant" ? (
        <div className="h-2 w-2 rounded-full bg-purple-500" />
      ) : (
        <div className="h-2 w-2 rounded-full bg-gray-500" />
      );
    }
    return <div className="h-2 w-2 rounded-full bg-gray-400" />;
  };

  const shouldHide = useMemo(
    () => !shouldDisplayTrailItem({ message_type: item.message_type, structured_data: item.structured_data }, structured),
    [item.message_type, item.structured_data, structured]
  );

  if (shouldHide) {
    return null;
  }

  const typeLabel = useMemo(() => {
    switch (item.message_type) {
      case "AssistantMessage":
        if (!assistantHasText && assistantHasTool) {
          return "";
        }
        return "Assistant";
      case "ResultMessage":
        return "Result";
      case "UserMessage":
        return "User";
      case "SystemMessage":
        return "System";
      default:
        return item.message_type ?? "Entry";
    }
  }, [item.message_type, assistantHasText, assistantHasTool]);

  const containerClass = `relative flex items-start gap-3 ${isToolOnlyAssistant ? 'gap-0 pl-6' : ''}`;
  
  return (
    <div className={containerClass}>
      <div className="mt-2">{renderIcon()}</div>
      <div className="relative flex-1">
        {showTimelineLine && (
          <div className="pointer-events-none absolute left-[-1.25rem] top-6 bottom-0 w-px bg-gray-200 dark:bg-gray-700" aria-hidden />
        )}
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-purple-500 dark:text-purple-300">
          <span>{typeLabel}</span>
        </div>
        <div className="mt-1 text-sm text-gray-900 dark:text-gray-100">
          {renderContent()}
        </div>
        <div className="mt-2 text-right text-xs text-gray-400 dark:text-gray-500">
          {formatTime(item.timestamp)}
        </div>
      </div>
    </div>
  );
};

export default AuditTrailItem;
