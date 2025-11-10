import {
  WorkshopTemplate,
  WorkshopSession,
  CreateSessionRequest,
  ReportResponse
} from '@/lib/types/workshop'

const API_BASE = '/api/workshops'

// -------------------- 模板相关 --------------------
/**
 * 获取所有可用模板
 */
export async function getTemplates(): Promise<WorkshopTemplate[]> {
  const response = await fetch(`${API_BASE}/templates`)

  if (!response.ok) {
    throw new Error(`Failed to fetch templates: ${response.statusText}`)
  }

  return response.json()
}

// -------------------- 会话管理 --------------------
/**
 * 创建并启动新会话
 */
export async function createSession(
  request: CreateSessionRequest
): Promise<WorkshopSession> {
  const response = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to create session')
  }

  return response.json()
}

/**
 * 获取会话详情
 */
export async function getSession(sessionId: string): Promise<WorkshopSession> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch session: ${response.statusText}`)
  }

  return response.json()
}

/**
 * 获取笔记本的所有会话
 */
export async function getNotebookSessions(
  notebookId: string
): Promise<WorkshopSession[]> {
  const response = await fetch(`${API_BASE}/notebooks/${notebookId}/sessions`)

  if (!response.ok) {
    throw new Error(`Failed to fetch notebook sessions: ${response.statusText}`)
  }

  return response.json()
}

/**
 * 删除会话
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    throw new Error(`Failed to delete session: ${response.statusText}`)
  }
}

/**
 * 获取会话报告
 */
export async function getSessionReport(
  sessionId: string
): Promise<ReportResponse> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/report`)

  if (!response.ok) {
    throw new Error(`Failed to fetch report: ${response.statusText}`)
  }

  return response.json()
}

// -------------------- 辅助函数 --------------------
/**
 * 轮询会话状态直到完成或失败
 * @param sessionId 会话ID
 * @param onUpdate 状态更新回调
 * @param pollInterval 轮询间隔（毫秒）
 * @returns 最终会话状态
 */
export async function pollSessionUntilComplete(
  sessionId: string,
  onUpdate?: (session: WorkshopSession) => void,
  pollInterval = 3000
): Promise<WorkshopSession> {
  const poll = async (): Promise<WorkshopSession> => {
    const session = await getSession(sessionId)

    // 触发更新回调
    if (onUpdate) {
      onUpdate(session)
    }

    // 检查状态
    if (session.status === 'completed' || session.status === 'failed') {
      return session
    }

    // 继续轮询
    await new Promise(resolve => setTimeout(resolve, pollInterval))
    return poll()
  }

  return poll()
}
