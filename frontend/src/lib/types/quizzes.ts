export type QuizStatus =
  | 'running'
  | 'completed'
  | 'failed'
  | 'pending'
  | 'submitted'
  | 'unknown'

export interface QuizTemplate {
  id: string
  name: string
  description: string
  quiz_type: string
  default_question_count: number
  difficulty_level: 'easy' | 'medium' | 'hard'
  instructions: string
  created: string
  updated: string
}

export interface Quiz {
  id: string
  title: string
  quiz_type: string
  question_count: number
  status: QuizStatus
  created: string
  updated: string
  notebook_id?: string
  source_ids?: string[]
  note_ids?: string[]
  questions?: QuizQuestion[]
}

export interface QuizQuestion {
  id: string
  type: 'multiple-choice' | 'true-false' | 'fill-blank' | 'problem-solving'
  question: string
  options?: string[]
  correct_answer: string
  explanation?: string
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface QuizProfile {
  id: string
  name: string
  description?: string
  quiz_types?: string[]
  difficulty_levels?: string[]
  default_question_count?: number
  question_provider?: string
  question_model?: string
  evaluation_provider?: string
  evaluation_model?: string
  default_instructions?: string
  time_limit_minutes?: number
  passing_score_percentage?: number
}

export interface QuizGenerationRequest {
  quiz_profile: string
  quiz_title: string
  content: string
  question_count: number
  quiz_type: string
  difficulty: string
  additional_instructions?: string
  quiz_template?: string
  notebook_id?: string
  source_ids?: string[]
  note_ids?: string[]
}

export interface QuizGenerationResponse {
  job_id: string
  status: string
  message: string
  quiz_title: string
  quiz_type: string
  quiz_id?: string
  estimated_duration?: number
}

export type QuizStatusGroup = 'running' | 'completed' | 'failed' | 'pending'

export type QuizStatusGroups = Record<QuizStatusGroup, Quiz[]>

export const ACTIVE_QUIZ_STATUSES: QuizStatus[] = [
  'running',
  'pending',
  'submitted',
]

export const FAILED_QUIZ_STATUSES: QuizStatus[] = ['failed']

/**
 * Groups quizzes by their status for organized display
 */
export function groupQuizzesByStatus(quizzes: Quiz[]): QuizStatusGroups {
  return quizzes.reduce<QuizStatusGroups>(
    (groups, quiz) => {
      const status = quiz.status || 'unknown'

      if (status === 'running') {
        groups.running.push(quiz)
        return groups
      }

      if (status === 'completed') {
        groups.completed.push(quiz)
        return groups
      }

      if (FAILED_QUIZ_STATUSES.includes(status)) {
        groups.failed.push(quiz)
        return groups
      }

      groups.pending.push(quiz)
      return groups
    },
    { running: [], completed: [], failed: [], pending: [] }
  )
}

/**
 * Calculates status counts for summary display
 */
export function calculateQuizStatusCounts(quizzes: Quiz[]) {
  const groups = groupQuizzesByStatus(quizzes)
  return {
    total: quizzes.length,
    running: groups.running.length,
    completed: groups.completed.length,
    failed: groups.failed.length,
    pending: groups.pending.length,
  }
}