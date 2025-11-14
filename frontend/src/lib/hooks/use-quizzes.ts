import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { quizzesApi, QuizTemplateInput } from '@/lib/api/quizzes'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import {
  ACTIVE_QUIZ_STATUSES,
  Quiz,
  QuizTemplate,
  QuizGenerationRequest,
  groupQuizzesByStatus,
  calculateQuizStatusCounts,
} from '@/lib/types/quizzes'

interface QuizStatusCounts {
  total: number
  running: number
  completed: number
  failed: number
  pending: number
}

/**
 * Checks if there are any active quizzes that might need auto-refresh
 */
function hasActiveQuizzes(quizzes: Quiz[]) {
  return quizzes.some((quiz) => {
    const status = quiz.status ?? 'unknown'
    return ACTIVE_QUIZ_STATUSES.includes(status)
  })
}

export function useQuiz(quizId: string) {
  return useQuery({
    queryKey: [QUERY_KEYS.quizzes, quizId],
    queryFn: () => quizzesApi.getQuiz(quizId),
    enabled: !!quizId, // Only fetch when quizId is available
  })
}

/**
 * Hook for managing quiz data with auto-refresh for active quizzes
 */
export function useQuizzes(options?: { autoRefresh?: boolean }) {
  const { autoRefresh = true } = options ?? {}

  const query = useQuery({
    queryKey: QUERY_KEYS.quizzes,
    queryFn: quizzesApi.listQuizzes,
    refetchInterval: (current) => {
      if (!autoRefresh) {
        return false
      }

      const data = current.state.data as Quiz[] | undefined
      if (!data || data.length === 0) {
        return false
      }

      return hasActiveQuizzes(data) ? 10_000 : false
    },
  })

  const quizzes = useMemo(() => query.data ?? [], [query.data])

  const statusGroups = useMemo(() => groupQuizzesByStatus(quizzes), [quizzes])

  const statusCounts = useMemo<QuizStatusCounts>(
    () => calculateQuizStatusCounts(quizzes),
    [quizzes]
  )

  const active = useMemo(() => hasActiveQuizzes(quizzes), [quizzes])

  return {
    ...query,
    quizzes,
    statusGroups,
    statusCounts,
    hasActiveQuizzes: active,
  }
}

/**
 * Hook for deleting a quiz with optimistic updates
 */
export function useDeleteQuiz() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (quizId: string) => quizzesApi.deleteQuiz(quizId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.quizzes })
      toast({
        title: 'Quiz deleted',
        description: 'Quiz has been removed successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete quiz',
        description: 'Please try again or check the server logs for details.',
        variant: 'destructive',
      })
    },
  })
}

/**
 * Hook for generating a new quiz
 */
export function useGenerateQuiz() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (payload: QuizGenerationRequest) => quizzesApi.generateQuiz(payload),
    onSuccess: async (response) => {
      // Immediately refetch to show the new quiz
      await queryClient.refetchQueries({ queryKey: QUERY_KEYS.quizzes })
      toast({
        title: 'Quiz generation started',
        description: `"${response.quiz_title}" is being created.`,
      })
    },
    onError: () => {
      toast({
        title: 'Failed to start quiz generation',
        description: 'Please try again in a moment.',
        variant: 'destructive',
      })
    },
  })
}

/**
 * Hook for managing quiz templates
 */
export function useQuizTemplates() {
  const query = useQuery({
    queryKey: QUERY_KEYS.quizTemplates,
    queryFn: quizzesApi.listQuizTemplates,
  })

  return {
    ...query,
    quizTemplates: query.data ?? [],
  }
}

/**
 * Hook for creating a new quiz template
 */
export function useCreateQuizTemplate() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (payload: QuizTemplateInput) => quizzesApi.createQuizTemplate(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.quizTemplates })
      toast({
        title: 'Quiz template created',
        description: 'The new template is ready to use.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to create quiz template',
        description: 'Double-check the form and try again.',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateQuizTemplate() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({
      templateId,
      payload,
    }: {
      templateId: string
      payload: QuizTemplateInput
    }) => quizzesApi.updateQuizTemplate(templateId, payload),
    onSuccess: () => {
      // Invalidate quiz templates queries to refresh the list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.quizTemplates })
    //   queryClient.invalidateQueries({ queryKey: QUERY_KEYS.quizTemplate })
      // Optionally invalidate quizzes if template changes affect generated quizzes
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.quizzes })
      toast({
        title: 'Quiz template updated',
        description: 'Changes saved successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update quiz template',
        description: 'Please try again later.',
        variant: 'destructive',
      })
    },
  })
}

/**
 * Hook for deleting a quiz template
 */
export function useDeleteQuizTemplate() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (templateId: string) => quizzesApi.deleteQuizTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.quizTemplates })
      toast({
        title: 'Quiz template deleted',
        description: 'Template removed successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete quiz template',
        description: 'Ensure the template is not in use and try again.',
        variant: 'destructive',
      })
    },
  })
}

export function useDuplicateQuizTemplate() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (templateId: string) => quizzesApi.duplicateQuizTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.quizTemplates })
      toast({
        title: 'Quiz template duplicated',
        description: 'A copy of the template has been created.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to duplicate quiz template',
        description: 'Please try again later.',
        variant: 'destructive',
      })
    },
  })
}