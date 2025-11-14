import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  WorkshopTemplate,
  CreateSessionRequest,
  AgentMessage
} from '@/lib/types/workshop'
import {
  getTemplates,
  createSession,
  getSession,
  getNotebookSessions,
  deleteSession,
  pollSessionUntilComplete
} from '@/lib/api/workshop'
import { toast } from 'sonner'

interface UseWorkshopOptions {
  notebookId: string
  autoStart?: boolean  // 自动启动轮询
  useStreaming?: boolean  // 使用SSE流式输出（默认true）
}

interface StreamingMessage {
  agent_id: string
  agent_name: string
  content: string
  round_number: number
  timestamp: string
  isComplete: boolean
  tool_calls?: Array<Record<string, any>>  // ✅ 新增: 工具调用记录
}

export function useWorkshop({ notebookId, autoStart = true, useStreaming = true }: UseWorkshopOptions) {
  const queryClient = useQueryClient()

  // -------------------- 状态管理 --------------------
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<WorkshopTemplate | null>(null)

  // -------------------- SSE流式状态 --------------------
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingMessages, setStreamingMessages] = useState<Map<string, StreamingMessage>>(new Map())
  const eventSourceRef = useRef<EventSource | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // -------------------- 查询：模板列表 --------------------
  const {
    data: templates = [],
    isLoading: templatesLoading
  } = useQuery({
    queryKey: ['workshop-templates'],
    queryFn: getTemplates,
    staleTime: 5 * 60 * 1000  // 5分钟缓存
  })

  // -------------------- 查询：笔记本会话列表 --------------------
  const {
    data: sessions = [],
    isLoading: sessionsLoading,
    refetch: refetchSessions
  } = useQuery({
    queryKey: ['workshop-sessions', notebookId],
    queryFn: () => getNotebookSessions(notebookId),
    enabled: !!notebookId
  })

  // -------------------- 查询：当前会话详情 --------------------
  const {
    data: currentSession,
    isLoading: sessionLoading,
    refetch: refetchSession
  } = useQuery({
    queryKey: ['workshop-session', currentSessionId],
    queryFn: () => getSession(currentSessionId!),
    enabled: !!currentSessionId && !isPolling,
    refetchInterval: false  // 手动控制轮询
  })

  // -------------------- Mutation：创建会话 --------------------
  const createSessionMutation = useMutation({
    mutationFn: (request: CreateSessionRequest) => createSession(request),
    onSuccess: (session) => {
      setCurrentSessionId(session.id)
      toast.success('Session created, starting...')

      // 启动轮询
      if (autoStart) {
        startPolling(session.id)
      }

      // 刷新会话列表
      refetchSessions()
    },
    onError: (error: Error) => {
      toast.error(`Failed to create session: ${error.message}`)
    }
  })

  // -------------------- Mutation：删除会话 --------------------
  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => deleteSession(sessionId),
    onSuccess: (_data, sessionId) => {
      toast.success('Session deleted')
      refetchSessions()

      // 如果删除的是当前会话，清空状态
      if (currentSessionId && currentSessionId === sessionId) {
        setCurrentSessionId(null)
      }
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete session: ${error.message}`)
    }
  })

  // -------------------- 轮询控制 --------------------
  const startPolling = useCallback(async (sessionId: string) => {
    if (isPolling) return

    setIsPolling(true)

    try {
      const finalSession = await pollSessionUntilComplete(
        sessionId,
        (updatedSession) => {
          // 每次轮询更新时，刷新缓存
          queryClient.setQueryData(
            ['workshop-session', sessionId],
            updatedSession
          )
        },
        3000  // 3秒轮询间隔
      )

      // 完成后显示通知
      if (finalSession.status === 'completed') {
        toast.success('Discussion completed!')
      } else if (finalSession.status === 'failed') {
        toast.error('Discussion failed, please retry')
      }

    } catch (error) {
      toast.error('Polling error, please refresh manually')
      console.error('Polling error:', error)
    } finally {
      setIsPolling(false)
      refetchSessions()  // 刷新会话列表
    }
  }, [isPolling, queryClient, refetchSessions])

  const stopPolling = useCallback(() => {
    setIsPolling(false)
  }, [])

  // -------------------- SSE流式方法 --------------------
  const createSessionWithStreaming = useCallback(
    async (mode: string, topic: string, context?: Record<string, unknown>) => {
      // ✅ 先停止之前的streaming（如果有）
      console.log('[Workshop] Creating new session, cleaning up previous connections first...')
      stopStreaming()

      setIsStreaming(true)
      setStreamingMessages(new Map())

      const request: CreateSessionRequest = {
        notebook_id: notebookId,
        mode,
        topic,
        context
      }

      try {
        // 使用fetch发起SSE请求
        const abortController = new AbortController()
        abortControllerRef.current = abortController

        // 直接连接后端，绕过 Next.js 代理以避免 SSE 缓冲问题
        const response = await fetch('http://localhost:5055/api/workshops/sessions/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
          signal: abortController.signal
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (!reader) {
          throw new Error('Response body is null')
        }

        let sessionId = ''
        let currentEventType = ''  // Track event type between lines

        // 读取SSE流
        while (true) {
          const { done, value } = await reader.read()

          if (done) break

          // 解码数据块
          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEventType = line.substring(6).trim()
              console.log('[SSE Frontend] Event type:', currentEventType)
              continue
            }

            if (line.startsWith('data:')) {
              const dataStr = line.substring(5).trim()
              if (!dataStr) continue

              try {
                const data = JSON.parse(dataStr)
                console.log('[SSE Frontend] Received event:', currentEventType, 'data:', data)

                // 根据事件类型处理数据
                if (currentEventType === 'session_created' && data.session_id) {
                  sessionId = data.session_id
                  setCurrentSessionId(sessionId)
                  console.log('[SSE Frontend] Session created:', sessionId)
                }

                else if (currentEventType === 'agent_start' && data.agent_id && data.round) {
                  const key = `${data.agent_id}-${data.round}`
                  console.log('[SSE Frontend] Agent started:', key)

                  // 初始化新的agent消息
                  setStreamingMessages(prev => {
                    const newMap = new Map(prev)
                    if (!newMap.has(key)) {
                      newMap.set(key, {
                        agent_id: data.agent_id,
                        agent_name: data.agent_id,
                        content: '',
                        round_number: data.round,
                        timestamp: new Date().toISOString(),
                        isComplete: false
                      })
                    }
                    return newMap
                  })
                }

                else if (currentEventType === 'agent_chunk' && data.agent_id && data.round && data.chunk) {
                  const key = `${data.agent_id}-${data.round}`
                  console.log('[SSE Frontend] Agent chunk:', key, 'length:', data.chunk.length)

                  // 累加内容
                  setStreamingMessages(prev => {
                    const newMap = new Map(prev)
                    const existing = newMap.get(key)

                    if (existing) {
                      newMap.set(key, {
                        ...existing,
                        content: existing.content + data.chunk,
                        timestamp: new Date().toISOString()
                      })
                    } else {
                      // 如果没有先收到agent_start，创建新消息
                      newMap.set(key, {
                        agent_id: data.agent_id,
                        agent_name: data.agent_id,
                        content: data.chunk,
                        round_number: data.round,
                        timestamp: new Date().toISOString(),
                        isComplete: false
                      })
                    }

                    return newMap
                  })
                }

                // ✅ 新增: 处理agent_complete事件（包含完整消息和tool_calls）
                else if (currentEventType === 'agent_complete' && data.agent_id && data.round) {
                  const key = `${data.agent_id}-${data.round}`
                  console.log('[SSE Frontend] Agent complete:', key, 'tool_calls:', data.tool_calls?.length || 0)

                  // 更新消息，添加tool_calls和完整内容
                  setStreamingMessages(prev => {
                    const newMap = new Map(prev)
                    const existing = newMap.get(key)

                    if (existing) {
                      // 更新现有消息，添加tool_calls
                      newMap.set(key, {
                        ...existing,
                        content: data.content || existing.content,  // 使用完整内容
                        tool_calls: data.tool_calls || [],
                        timestamp: data.timestamp || existing.timestamp,
                        isComplete: true
                      })
                    } else {
                      // 如果之前没有收到chunk，创建完整消息
                      newMap.set(key, {
                        agent_id: data.agent_id,
                        agent_name: data.agent_id,
                        content: data.content || '',
                        round_number: data.round,
                        timestamp: data.timestamp || new Date().toISOString(),
                        tool_calls: data.tool_calls || [],
                        isComplete: true
                      })
                    }

                    return newMap
                  })
                }

                else if (currentEventType === 'session_complete' && data.session_id) {
                  console.log('[SSE Frontend] Session completed:', data.session_id)
                  toast.success('Discussion completed!')

                  // 标记所有消息为完成
                  setStreamingMessages(prev => {
                    const newMap = new Map(prev)
                    newMap.forEach((msg, key) => {
                      newMap.set(key, { ...msg, isComplete: true })
                    })
                    return newMap
                  })

                  // 获取最终session
                  if (sessionId) {
                    await getSession(sessionId).then(finalSession => {
                      queryClient.setQueryData(['workshop-session', sessionId], finalSession)
                    })
                    refetchSessions()
                  }
                }

                else if (currentEventType === 'error' && data.error) {
                  console.error('[SSE Frontend] Error event:', data.error)
                  toast.error(`Streaming error: ${data.error}`)
                }

                // 重置事件类型
                currentEventType = ''
              } catch (e) {
                console.error('Error parsing SSE data:', e, 'line:', line)
              }
            }
          }
        }

      } catch (error: any) {
        if (error.name === 'AbortError') {
          console.log('SSE connection aborted')
        } else {
          console.error('SSE error:', error)
          toast.error('Streaming error, falling back to polling...')

          // Fallback到轮询模式
          if (currentSessionId) {
            startPolling(currentSessionId)
          }
        }
      } finally {
        setIsStreaming(false)
        abortControllerRef.current = null
      }
    },
    [notebookId, queryClient, refetchSessions, startPolling, currentSessionId, stopStreaming]
  )

  const stopStreaming = useCallback(() => {
    console.log('[Workshop] Stopping streaming and cleaning up...')

    // 中断fetch请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      console.log('[Workshop] Aborted fetch request')
    }

    // 关闭EventSource连接
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
      console.log('[Workshop] Closed EventSource connection')
    }

    // 清理状态
    setIsStreaming(false)
    setStreamingMessages(new Map())
    console.log('[Workshop] Cleanup complete')
  }, [])

  // ✅ 清理effect - 当组件卸载或notebook切换时自动清理
  useEffect(() => {
    return () => {
      console.log('[Workshop] Component unmounting, cleaning up streaming...')
      stopStreaming()
    }
  }, [stopStreaming])

  // ✅ 监听notebookId变化，切换notebook时也清理
  useEffect(() => {
    return () => {
      if (isStreaming) {
        console.log('[Workshop] Notebook changed, cleaning up streaming...')
        stopStreaming()
      }
    }
  }, [notebookId, isStreaming, stopStreaming])

  // -------------------- 公共方法 --------------------
  const createNewSession = useCallback(
    async (mode: string, topic: string, context?: Record<string, unknown>) => {
      // 根据 useStreaming 选项决定使用哪种方式
      if (useStreaming) {
        return createSessionWithStreaming(mode, topic, context)
      } else {
        const request: CreateSessionRequest = {
          notebook_id: notebookId,
          mode,
          topic,
          context
        }
        return createSessionMutation.mutate(request)
      }
    },
    [notebookId, useStreaming, createSessionWithStreaming, createSessionMutation]
  )

  const selectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
  }, [])

  const removeSession = useCallback((sessionId: string) => {
    deleteSessionMutation.mutate(sessionId)
  }, [deleteSessionMutation])

  // -------------------- 返回值 --------------------
  return {
    // 数据
    templates,
    sessions,
    currentSession,
    selectedTemplate,

    // 加载状态
    isLoading: templatesLoading || sessionsLoading || sessionLoading,
    isCreatingSession: createSessionMutation.isPending,
    isDeletingSession: deleteSessionMutation.isPending,
    isPolling,
    isStreaming,

    // 流式消息
    streamingMessages,

    // 操作方法
    setSelectedTemplate,
    createNewSession,
    createSessionWithStreaming,  // 显式导出流式方法
    selectSession,
    removeSession,
    startPolling,
    stopPolling,
    stopStreaming,
    refetchSession,
    refetchSessions
  }
}
