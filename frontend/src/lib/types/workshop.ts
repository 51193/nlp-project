// ============================================
// 思维工坊类型定义
// ============================================

// -------------------- Agent信息 --------------------
export interface AgentInfo {
  id: string              // Agent ID
  name: string            // Agent名称（中文）
  role: string            // Agent角色（英文）
  avatar: string          // Avatar emoji
  color: string           // 颜色（hex）
}

// -------------------- 模板 --------------------
export interface WorkshopTemplate {
  mode_id: 'dialectical_mode' | 'brainstorm_mode'
  name: string
  description: string
  icon: string
  agents: AgentInfo[]
  use_cases: string[]
  estimated_time: string
}

// -------------------- 工具调用 --------------------
export interface ToolCall {
  tool: string            // 工具名称
  input: unknown          // 输入参数
  output: string          // 输出结果
}

// -------------------- Agent消息 --------------------
export interface AgentMessage {
  agent_id: string
  agent_name: string
  content: string
  round_number: number
  timestamp: string
  tool_calls: ToolCall[]
}

// -------------------- 会话 --------------------
export type SessionStatus = 'created' | 'in_progress' | 'completed' | 'failed'

export interface WorkshopSession {
  id: string
  notebook_id: string
  mode: string
  topic: string
  status: SessionStatus
  messages: AgentMessage[]
  final_report: string | null
  created: string
  updated: string
  total_rounds: number
  agent_count: number
}

// -------------------- API请求/响应 --------------------
export interface CreateSessionRequest {
  notebook_id: string
  mode: string
  topic: string
  context?: Record<string, unknown>
}

export type SessionResponse = WorkshopSession

export type TemplateResponse = WorkshopTemplate

export interface ReportResponse {
  session_id: string
  report: string
}

// -------------------- UI状态 --------------------
export type WorkshopMode = 'chat' | 'workshop'  // Chat模式 vs 思维工坊模式

export interface WorkshopUIState {
  mode: WorkshopMode
  selectedTemplate: WorkshopTemplate | null
  currentSession: WorkshopSession | null
  isLoading: boolean
  error: string | null
}

// -------------------- 流式显示相关 --------------------
/**
 * 用于前端打字机效果的消息状态
 */
export interface StreamingMessage extends AgentMessage {
  isStreaming: boolean       // 是否正在流式显示
  displayedContent: string   // 当前已显示的内容
  fullContent: string        // 完整内容
}

/**
 * 虚拟滚动项
 */
export interface VirtualListItem {
  index: number
  message: AgentMessage
  height: number  // 预估高度
}
