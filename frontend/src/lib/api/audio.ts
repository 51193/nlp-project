import apiClient from './client'

export interface TranscriptionResponse {
  text: string
  language?: string | null
}

export async function transcribeAudio(
  blob: Blob,
  options?: {
    filename?: string
    language?: string
    prompt?: string
  }
): Promise<TranscriptionResponse> {
  const formData = new FormData()
  const fileName = options?.filename || 'recording.webm'
  const normalizedType =
    blob.type && blob.type.length > 0
      ? blob.type.split(';', 1)[0] || 'audio/webm'
      : 'audio/webm'
  const file =
    blob instanceof File
      ? new File([blob], fileName, { type: normalizedType })
      : new File([blob], fileName, { type: normalizedType })

  formData.append('file', file)

  if (options?.language) {
    formData.append('language', options.language)
  }

  if (options?.prompt) {
    formData.append('prompt', options.prompt)
  }

  const response = await apiClient.post<TranscriptionResponse>('/audio/transcriptions', formData)
  return response.data
}

