import apiClient from './client'
import {
  Quiz,
  QuizTemplate,
  QuizGenerationRequest,
  QuizGenerationResponse,
  QuizProfile,
} from '@/lib/types/quizzes'


export type QuizTemplateInput = Omit<QuizTemplate, 'id' | 'created' | 'updated'>

/**
 * Quizzes API module
 * 
 * Provides methods for interacting with quiz-related endpoints including
 * generation, listing, and management of quizzes and templates.
 */
export const quizzesApi = {
  // Quiz management
  listQuizzes: async (): Promise<Quiz[]> => {
    const response = await apiClient.get<Quiz[]>('/quizzes')
    return response.data
  },

  getQuiz: async (quizId: string): Promise<Quiz> => {
    const response = await apiClient.get<Quiz>(`/quizzes/${quizId}`)
    return response.data
  },

  deleteQuiz: async (quizId: string): Promise<void> => {
    await apiClient.delete(`/quizzes/${quizId}`)
  },

  // Quiz generation
  generateQuiz: async (payload: QuizGenerationRequest): Promise<QuizGenerationResponse> => {
   
    const backendPayload = {
      quiz_profile: 'default',
      quiz_title: payload.quiz_title,
      content: payload.content,
      question_count: payload.question_count,
      quiz_type: payload.quiz_type,
      difficulty: 'medium', 
      additional_instructions: payload.additional_instructions
    }
    
    const response = await apiClient.post<QuizGenerationResponse>(
      '/quizzes/generate',
      backendPayload
    )
    return response.data
  },

  // Quiz templates management
  listQuizTemplates: async (): Promise<QuizTemplate[]> => {
    const response = await apiClient.get<QuizTemplate[]>('/quizzes/templates')
    return response.data
  },

  createQuizTemplate: async (payload: QuizTemplateInput): Promise<QuizTemplate> => {
    const response = await apiClient.post<QuizTemplate>(
      '/quizzes/templates',
      payload
    )
    return response.data
  },

  updateQuizTemplate: async (templateId: string, payload: QuizTemplateInput): Promise<QuizTemplate> => {
    const response = await apiClient.put<QuizTemplate>(
      `/quizzes/templates/${templateId}`,
      payload
    )
    return response.data
  },

  deleteQuizTemplate: async (templateId: string): Promise<void> => {
    await apiClient.delete(`/quizzes/templates/${templateId}`)
  },

  duplicateQuizTemplate: async (templateId: string): Promise<QuizTemplate> => {
    const response = await apiClient.post<QuizTemplate>(
      `/quizzes/templates/${templateId}/duplicate`
    )
    return response.data
  },

  getQuizProfiles: async (): Promise<QuizProfile[]> => {
    try {
      const response = await apiClient.get<QuizProfile[]>('/quizzes/profiles')
      return response.data
    } catch (error) {
      console.error('Failed to fetch quiz profiles', error)
      return [{
        id: 'default',
        name: 'Default Profile',
        description: 'Standard quiz generation profile'
      }]
    }
  },
}