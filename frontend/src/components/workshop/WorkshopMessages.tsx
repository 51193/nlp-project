'use client'

import { useMemo, useRef, useEffect, useState } from 'react'
import { WorkshopSession, AgentInfo, AgentMessage } from '@/lib/types/workshop'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, Wrench, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useTypewriter } from '@/lib/hooks/use-typewriter'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface StreamingMessage {
  agent_id: string
  agent_name: string
  content: string
  round_number: number
  timestamp: string
  isComplete: boolean
  tool_calls?: Array<{ tool: string; input: unknown; output: string }>  // ✅ 新增: 工具调用记录
}

interface WorkshopMessagesProps {
  session: WorkshopSession
  agentsInfo: AgentInfo[]  // 从模板获取
  isPolling?: boolean
  isStreaming?: boolean
  streamingMessages?: Map<string, StreamingMessage>
}

/**
 * 工具调用展示组件 - 可折叠
 */
function ToolCallDisplay({ toolCall }: { toolCall: { tool: string; input: unknown; output: string } }) {
  const [isOpen, setIsOpen] = useState(false)

  // 格式化输入参数
  const formatInput = (input: unknown): string => {
    if (typeof input === 'string') {
      return input
    }
    if (typeof input === 'object' && input !== null) {
      // 提取关键参数
      const obj = input as Record<string, unknown>
      if ('query' in obj) {
        return String(obj.query)
      }
      return JSON.stringify(input)
    }
    return String(input)
  }

  // 简化输出（如果太长则截断）
  const formatOutput = (output: string, maxLength: number = 150): { short: string; isTruncated: boolean } => {
    if (!output) return { short: '(empty)', isTruncated: false }

    // 检查是否是notebook_reader的输出
    if (output.includes('Complete Notebook Content')) {
      // 提取sources和notes的数量和标题
      const sourcesMatch = output.match(/This notebook contains (\d+) sources? and (\d+) notes?/)
      if (sourcesMatch) {
        const sourcesCount = sourcesMatch[1]
        const notesCount = sourcesMatch[2]

        // 提取source标题
        const sourceTitles: string[] = []
        const sourceMatches = output.matchAll(/### Source \d+: (.+)\n/g)
        for (const match of sourceMatches) {
          sourceTitles.push(match[1])
        }

        let summary = `Read ${sourcesCount} source${parseInt(sourcesCount) > 1 ? 's' : ''} and ${notesCount} note${parseInt(notesCount) > 1 ? 's' : ''}`
        if (sourceTitles.length > 0) {
          summary += ` (${sourceTitles.join(', ')})`
        }

        return {
          short: summary,
          isTruncated: true
        }
      }
    }

    // 尝试解析JSON
    try {
      const parsed = JSON.parse(output)
      // 如果是Tavily搜索结果
      if (parsed.results && Array.isArray(parsed.results)) {
        const resultCount = parsed.results.length
        const firstTitle = parsed.results[0]?.title || 'No title'
        return {
          short: `Found ${resultCount} web results. Top: "${firstTitle}"`,
          isTruncated: true
        }
      }
    } catch {
      // 不是JSON，直接处理
    }

    if (output.length <= maxLength) {
      return { short: output, isTruncated: false }
    }

    return {
      short: output.substring(0, maxLength) + '...',
      isTruncated: true
    }
  }

  // 格式化展开状态的详细输出
  const formatExpandedOutput = (output: string): JSX.Element => {
    if (!output) return <span className="text-muted-foreground">(empty)</span>

    // notebook_reader: 显示文档列表
    if (output.includes('Complete Notebook Content')) {
      const sourcesMatch = output.match(/This notebook contains (\d+) sources? and (\d+) notes?/)

      if (sourcesMatch) {
        const sourcesCount = sourcesMatch[1]
        const notesCount = sourcesMatch[2]

        // 提取source标题
        const sourceTitles: string[] = []
        const sourceMatches = output.matchAll(/### Source \d+: (.+)\n/g)
        for (const match of sourceMatches) {
          sourceTitles.push(match[1])
        }

        // 提取note标题
        const noteTitles: string[] = []
        const noteMatches = output.matchAll(/### Note \d+: (.+)\n/g)
        for (const match of noteMatches) {
          if (match[1] !== 'None') {
            noteTitles.push(match[1])
          }
        }

        return (
          <div className="space-y-2">
            <div className="font-medium">📚 Notebook Content Summary</div>
            <div className="text-muted-foreground">
              {sourcesCount} source(s) and {notesCount} note(s)
            </div>

            {sourceTitles.length > 0 && (
              <div>
                <div className="font-medium text-xs mb-1">Sources:</div>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                  {sourceTitles.map((title, i) => (
                    <li key={i}>{title}</li>
                  ))}
                </ul>
              </div>
            )}

            {noteTitles.length > 0 && (
              <div>
                <div className="font-medium text-xs mb-1">Notes:</div>
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                  {noteTitles.map((title, i) => (
                    <li key={i}>{title}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )
      }
    }

    // tavily_search: 显示搜索结果列表
    try {
      const parsed = JSON.parse(output)
      if (parsed.results && Array.isArray(parsed.results)) {
        return (
          <div className="space-y-2">
            <div className="font-medium">🔍 Web Search Results ({parsed.results.length})</div>
            <ul className="space-y-2">
              {parsed.results.slice(0, 5).map((result: { title: string; url: string; content?: string }, i: number) => (
                <li key={i} className="border-l-2 border-muted pl-2">
                  <div className="font-medium text-xs">{result.title}</div>
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline break-all"
                  >
                    {result.url}
                  </a>
                  {result.content && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {result.content.substring(0, 150)}...
                    </p>
                  )}
                </li>
              ))}
            </ul>
            {parsed.results.length > 5 && (
              <div className="text-xs text-muted-foreground">
                ... and {parsed.results.length - 5} more results
              </div>
            )}
          </div>
        )
      }
    } catch {
      // Not JSON, fall through
    }

    // Default: truncate to 500 chars
    if (output.length > 500) {
      return (
        <div className="space-y-2">
          <div className="text-muted-foreground">
            {output.substring(0, 500)}...
          </div>
          <div className="text-xs text-muted-foreground italic">
            (Content truncated - {output.length} characters total)
          </div>
        </div>
      )
    }

    return <div className="break-words whitespace-pre-wrap">{output}</div>
  }

  const inputText = formatInput(toolCall.input)
  const { short: outputShort, isTruncated } = formatOutput(toolCall.output)

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="bg-muted/50 rounded-md overflow-hidden">
        <CollapsibleTrigger className="w-full">
          <div className="flex items-center justify-between p-3 hover:bg-muted/70 transition-colors">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <Badge variant="secondary" className="text-xs flex-shrink-0">
                {toolCall.tool}
              </Badge>
              <span className="text-xs text-muted-foreground truncate">
                {inputText}
              </span>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0 ml-2">
              {isTruncated && (
                <Badge variant="outline" className="text-xs">
                  {isOpen ? 'Hide' : 'Show'} full
                </Badge>
              )}
              {isOpen ? (
                <ChevronUp className="h-3 w-3 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-3 w-3 text-muted-foreground" />
              )}
            </div>
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="px-3 pb-3 space-y-2 text-xs border-t">
            <div className="pt-2">
              <span className="text-muted-foreground font-medium">Input:</span>
              <pre className="mt-1 p-2 bg-background/50 rounded text-xs overflow-x-auto">
                <code className="break-all">{inputText}</code>
              </pre>
            </div>
            <div>
              <span className="text-muted-foreground font-medium">Output:</span>
              <div className="mt-1 p-2 bg-background/50 rounded text-xs overflow-x-auto max-h-64 overflow-y-auto">
                {formatExpandedOutput(toolCall.output)}
              </div>
            </div>
          </div>
        </CollapsibleContent>

        {/* Collapsed view - show summary */}
        {!isOpen && (
          <div className="px-3 pb-3 text-xs">
            <span className="text-muted-foreground">Result: </span>
            <span className="break-words">{outputShort}</span>
          </div>
        )}
      </div>
    </Collapsible>
  )
}

/**
 * Integrator JSON美化展示组件
 * 用于头脑风暴模式的integrator agent输出
 */
function IntegratorJsonView({ jsonContent }: { jsonContent: string }) {
  try {
    // 提取JSON代码块 (支持```json```格式或纯JSON)
    let jsonMatch = jsonContent.match(/```json\s*(\{[\s\S]*?\})\s*```/) ||
                    jsonContent.match(/(\{[\s\S]*"top_ideas"[\s\S]*\})/)

    if (jsonMatch) {
      // 清理JSON字符串（移除可能的trailing commas等）
      let jsonStr = jsonMatch[1]
        .replace(/,\s*}/g, '}')  // 移除对象中的trailing comma
        .replace(/,\s*]/g, ']')  // 移除数组中的trailing comma
        .trim()

      const parsed = JSON.parse(jsonStr)
      const topIdeas = parsed.top_ideas || []

      // 边框颜色映射
      const getBorderColor = (rank: number) => {
        if (rank === 1) return '#22c55e' // 绿色
        if (rank === 2) return '#3b82f6' // 蓝色
        return '#f59e0b' // 橙色
      }

      // 风险等级徽章variant
      const getRiskVariant = (level: string): "destructive" | "secondary" | "outline" => {
        if (level === 'High') return 'destructive'
        if (level === 'Medium') return 'secondary'
        return 'outline'
      }

      return (
        <div className="space-y-4">
          <div className="font-semibold text-base mb-3">🎯 Top 3 Integrated Ideas</div>

          {topIdeas.map((idea: any, idx: number) => (
            <Card
              key={idx}
              className="border-l-4"
              style={{ borderLeftColor: getBorderColor(idea.rank) }}
            >
              <CardContent className="pt-4 space-y-3">
                {/* 排名和标题 */}
                <div className="flex items-start gap-3">
                  <Badge variant="default" className="flex-shrink-0">#{idea.rank}</Badge>
                  <h3 className="font-semibold text-base flex-1">{idea.title}</h3>
                </div>

                {/* 描述 */}
                <p className="text-sm text-muted-foreground">{idea.description}</p>

                {/* 评分指标 */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <div className="text-xs text-muted-foreground">Innovation</div>
                    <div className="text-lg font-bold">{idea.innovation_score}/10</div>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <div className="text-xs text-muted-foreground">Feasibility</div>
                    <div className="text-lg font-bold">{idea.feasibility_score}/10</div>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <div className="text-xs text-muted-foreground">Impact</div>
                    <div className="text-lg font-bold">{idea.impact_score}/10</div>
                  </div>
                </div>

                {/* 风险等级 */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Risk Level:</span>
                  <Badge variant={getRiskVariant(idea.risk_level)}>
                    {idea.risk_level}
                  </Badge>
                </div>

                {/* 来源 */}
                {idea.sources && idea.sources.length > 0 && (
                  <div className="text-xs">
                    <span className="text-muted-foreground">Sources: </span>
                    <span>{idea.sources.join(', ')}</span>
                  </div>
                )}

                {/* 证据 */}
                {idea.evidence && (
                  <div className="text-xs">
                    <span className="text-muted-foreground font-medium">Evidence: </span>
                    <span className="text-muted-foreground">{idea.evidence}</span>
                  </div>
                )}

                {/* 实施步骤 (可折叠) */}
                {idea.implementation_steps && idea.implementation_steps.length > 0 && (
                  <details className="text-xs">
                    <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
                      ▸ Implementation Steps ({idea.implementation_steps.length})
                    </summary>
                    <ol className="list-decimal list-inside mt-2 space-y-1 text-muted-foreground pl-2">
                      {idea.implementation_steps.map((step: string, i: number) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </details>
                )}

                {/* 风险和缓解措施 (可折叠) */}
                {idea.risks_and_mitigation && idea.risks_and_mitigation.length > 0 && (
                  <details className="text-xs">
                    <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
                      ▸ Risks & Mitigation ({idea.risks_and_mitigation.length})
                    </summary>
                    <ul className="list-disc list-inside mt-2 space-y-1 text-muted-foreground pl-2">
                      {idea.risks_and_mitigation.map((item: string, i: number) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </CardContent>
            </Card>
          ))}

          {/* 优先级推荐 */}
          {parsed.recommended_priority && parsed.recommended_priority.length > 0 && (
            <div className="mt-4 p-4 bg-muted/30 rounded-lg">
              <div className="font-medium text-sm mb-2">📋 Recommended Priority</div>
              <div className="text-sm text-muted-foreground">
                {parsed.recommended_priority.join(' → ')}
              </div>
              {parsed.priority_reasoning && (
                <p className="text-xs text-muted-foreground mt-2">
                  {parsed.priority_reasoning}
                </p>
              )}
            </div>
          )}
        </div>
      )
    }
  } catch (e) {
    // JSON解析失败，返回null使用默认渲染
    console.error('Failed to parse integrator JSON:', e)
  }

  return null
}

/**
 * 单个Agent消息组件 - 支持打字机效果
 */
function AgentMessageCard({
  message,
  agent,
  enableTypewriter = false
}: {
  message: AgentMessage
  agent: AgentInfo
  enableTypewriter?: boolean
}) {
  const { displayedText, isTyping } = useTypewriter({
    text: message.content,
    speed: 20,  // 20ms per character
    enabled: enableTypewriter
  })

  // ✅ 检测是否是Integrator的JSON输出
  const isIntegratorJson = agent.id === 'integrator' && (
    message.content.includes('```json') ||
    (message.content.includes('"top_ideas"') && message.content.includes('"rank"'))
  )

  return (
    <Card className="overflow-hidden w-full max-w-full">
      {/* Agent头部 */}
      <div
        className="px-4 py-2 flex items-center gap-3 overflow-hidden"
        style={{ backgroundColor: `${agent.color}15` }}
      >
        <span className="text-2xl flex-shrink-0">{agent.avatar}</span>
        <div className="flex-1 min-w-0 overflow-hidden">
          <p className="font-medium text-sm truncate">{message.agent_name}</p>
          <p className="text-xs text-muted-foreground">
            Round {message.round_number}
          </p>
        </div>
        {isTyping && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground flex-shrink-0">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Typing...</span>
          </div>
        )}
      </div>

      {/* 消息内容 */}
      <CardContent className="pt-4 overflow-hidden">
        {isIntegratorJson ? (
          // ✅ Integrator使用特殊JSON渲染
          <IntegratorJsonView jsonContent={displayedText} /> || (
            // 如果JSON解析失败，降级到Markdown渲染
            <div className="prose prose-sm max-w-full dark:prose-invert">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="break-words whitespace-pre-wrap mb-2">{children}</p>,
                  code: ({ className, children }) => {
                    if (!className) {
                      return <code className="break-all bg-muted px-1 py-0.5 rounded text-xs">{children}</code>
                    }
                    return <code className="break-all">{children}</code>
                  },
                  pre: ({ children }) => (
                    <pre className="overflow-x-auto bg-muted p-2 rounded text-xs my-2 max-w-full">
                      {children}
                    </pre>
                  ),
                }}
              >
                {displayedText}
              </ReactMarkdown>
            </div>
          )
        ) : (
          // 其他Agent使用标准Markdown渲染
          <div className="prose prose-sm max-w-full dark:prose-invert">
            <ReactMarkdown
              components={{
                // Ensure proper text wrapping for all elements
                p: ({ children }) => <p className="break-words whitespace-pre-wrap mb-2">{children}</p>,
                code: ({ className, children }) => {
                  // Inline code
                  if (!className) {
                    return <code className="break-all bg-muted px-1 py-0.5 rounded text-xs">{children}</code>
                  }
                  // Code block
                  return <code className="break-all">{children}</code>
                },
                pre: ({ children }) => (
                  <pre className="overflow-x-auto bg-muted p-2 rounded text-xs my-2 max-w-full">
                    {children}
                  </pre>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    className="text-primary underline break-all"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {displayedText}
            </ReactMarkdown>
          </div>
        )}

        {/* 工具调用记录 */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <Wrench className="h-3 w-3" />
              Tool Calls ({message.tool_calls.length})
            </p>
            {message.tool_calls.map((toolCall, tcIdx) => (
              <ToolCallDisplay key={tcIdx} toolCall={toolCall} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function WorkshopMessages({
  session,
  agentsInfo,
  isPolling = false,
  isStreaming = false,
  streamingMessages = new Map()
}: WorkshopMessagesProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [lastMessageCount, setLastMessageCount] = useState(0)

  // 创建Agent ID到信息的映射
  const agentMap = useMemo(() => {
    const map: Record<string, AgentInfo> = {}
    agentsInfo.forEach(agent => {
      map[agent.id] = agent
    })
    return map
  }, [agentsInfo])

  // 状态标识
  const statusInfo = useMemo(() => {
    switch (session.status) {
      case 'created':
        return { label: 'Created', color: 'bg-blue-500' }
      case 'in_progress':
        return { label: 'In Progress', color: 'bg-yellow-500' }
      case 'completed':
        return { label: 'Completed', color: 'bg-green-500' }
      case 'failed':
        return { label: 'Failed', color: 'bg-red-500' }
    }
  }, [session.status])

  // 自动滚动到底部（当有新消息或流式消息时）
  useEffect(() => {
    if (session.messages.length > lastMessageCount || isStreaming) {
      // 有新消息或正在流式传输，滚动到底部
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
      setLastMessageCount(session.messages.length)
    }
  }, [session.messages.length, lastMessageCount, isStreaming, streamingMessages])

  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {/* 会话头部信息 */}
      <div className="px-4 py-3 border-b bg-muted/30 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${statusInfo.color}`} />
            <div className="min-w-0 flex-1">
              <h3 className="font-medium text-sm truncate">{session.topic}</h3>
              <p className="text-xs text-muted-foreground">
                {session.total_rounds} rounds · {session.agent_count} agents
              </p>
            </div>
          </div>

          <Badge variant="outline" className="text-xs flex-shrink-0">
            {statusInfo.label}
          </Badge>
        </div>
      </div>

      {/* 消息列表 - 使用ScrollArea with horizontal scroll */}
      <ScrollArea className="flex-1 min-h-0 w-full overflow-x-auto" ref={scrollAreaRef}>
        <div className="p-4 space-y-4 min-w-full">
          {session.messages.length === 0 && !isPolling && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center text-muted-foreground">
                <p className="text-sm">Waiting for discussion to start...</p>
              </div>
            </div>
          )}

          {session.messages.map((message, idx) => {
            const agent = agentMap[message.agent_id] || {
              id: message.agent_id,
              name: message.agent_name,
              role: message.agent_name,
              avatar: '🤖',
              color: '#6366f1'
            }

            // 只对最新的消息启用打字机效果（且会话正在进行中）
            const isLatestMessage = idx === session.messages.length - 1
            const enableTypewriter = isLatestMessage && session.status === 'in_progress'

            return (
              <AgentMessageCard
                key={`${message.agent_id}-${message.round_number}-${idx}`}
                message={message}
                agent={agent}
                enableTypewriter={enableTypewriter}
              />
            )
          })}

          {/* 流式消息（实时显示） */}
          {isStreaming && Array.from(streamingMessages.entries()).map(([key, streamMsg]) => {
            const agent = agentMap[streamMsg.agent_id] || {
              id: streamMsg.agent_id,
              name: streamMsg.agent_name,
              role: streamMsg.agent_name,
              avatar: '🤖',
              color: '#6366f1'
            }

            return (
              <AgentMessageCard
                key={`streaming-${key}`}
                message={{
                  agent_id: streamMsg.agent_id,
                  agent_name: streamMsg.agent_name,
                  content: streamMsg.content,
                  round_number: streamMsg.round_number,
                  timestamp: streamMsg.timestamp,
                  tool_calls: streamMsg.tool_calls || [],  // ✅ 使用流式消息中的tool_calls
                  error: false,
                  message_type: 'statement',
                  references: []
                }}
                agent={agent}
                enableTypewriter={false}  // 内容已经是流式的，不需要本地打字机效果
              />
            )
          })}

          {/* 流式中提示 */}
          {isStreaming && (
            <div className="flex items-center justify-center gap-2 text-muted-foreground py-4">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Streaming discussion in real-time...</span>
            </div>
          )}

          {/* 轮询中提示 */}
          {isPolling && session.messages.length > 0 && (
            <div className="flex items-center justify-center gap-2 text-muted-foreground py-4">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Discussion in progress, please wait...</span>
            </div>
          )}

          {/* 失败提示 */}
          {session.status === 'failed' && (
            <Card className="bg-destructive/5 border-destructive/20">
              <CardContent className="pt-6">
                <div className="text-center text-destructive">
                  <p className="text-sm font-medium">Discussion failed</p>
                  <p className="text-xs mt-1">Please check backend logs or retry</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 滚动锚点 */}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
    </div>
  )
}
