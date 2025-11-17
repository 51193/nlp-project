import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

interface UseAudioRecorderOptions {
  mimeType?: string
  maxDurationMs?: number
}

interface UseAudioRecorderResult {
  isSupported: boolean
  isRecording: boolean
  audioBlob: Blob | null
  error: string | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  reset: () => void
}

const DEFAULT_MAX_DURATION = 60_000 // 60 秒上限，避免产生超大文件

export function useAudioRecorder(options?: UseAudioRecorderOptions): UseAudioRecorderResult {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const stopTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isSupported = useMemo(
    () => typeof window !== 'undefined' && typeof window.MediaRecorder !== 'undefined',
    []
  )

  const clearTimeoutRef = () => {
    if (stopTimeoutRef.current) {
      clearTimeout(stopTimeoutRef.current)
      stopTimeoutRef.current = null
    }
  }

  const cleanupStream = () => {
    const recorder = mediaRecorderRef.current
    if (recorder?.stream) {
      recorder.stream.getTracks().forEach((track) => track.stop())
    }
  }

  const reset = useCallback(() => {
    setAudioBlob(null)
    setError(null)
    chunksRef.current = []
  }, [])

  const handleStop = useCallback(() => {
    const recorder = mediaRecorderRef.current
    if (!recorder) return
    cleanupStream()
    setIsRecording(false)

    if (chunksRef.current.length === 0) {
      setAudioBlob(null)
      return
    }

    const mime = options?.mimeType || recorder.mimeType || 'audio/webm'
    const blob = new Blob(chunksRef.current, { type: mime })
    chunksRef.current = []
    setAudioBlob(blob)
  }, [options?.mimeType])

  const startRecording = useCallback(async () => {
    if (!isSupported) {
      setError('当前浏览器不支持语音输入')
      return
    }
    try {
      reset()
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, {
        mimeType: options?.mimeType,
      })

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) {
          chunksRef.current.push(event.data)
        }
      }
      recorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error)
        setError('录音过程中出现错误')
        cleanupStream()
        setIsRecording(false)
      }
      recorder.onstop = handleStop

      recorder.start()
      mediaRecorderRef.current = recorder
      setIsRecording(true)

      const autoStopMs = options?.maxDurationMs ?? DEFAULT_MAX_DURATION
      clearTimeoutRef()
      stopTimeoutRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop()
        }
      }, autoStopMs)
    } catch (err) {
      console.error('Failed to start recording', err)
      setError('无法访问麦克风，请检查权限设置')
    }
  }, [handleStop, isSupported, options?.maxDurationMs, options?.mimeType, reset])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    clearTimeoutRef()
  }, [])

  useEffect(() => {
    return () => {
      clearTimeoutRef()
      if (mediaRecorderRef.current) {
        if (mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop()
        }
      }
      cleanupStream()
    }
  }, [])

  return {
    isSupported,
    isRecording,
    audioBlob,
    error,
    startRecording,
    stopRecording,
    reset,
  }
}

