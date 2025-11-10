import { useState, useEffect, useRef } from 'react'

interface UseTypewriterOptions {
  text: string
  speed?: number  // 每个字符的延迟时间（毫秒）
  enabled?: boolean  // 是否启用打字机效果
  onComplete?: () => void  // 完成回调
}

/**
 * 打字机效果Hook - 逐字显示文本
 * 用于实现类似ChatGPT的流式输出效果
 */
export function useTypewriter({
  text,
  speed = 20,
  enabled = true,
  onComplete
}: UseTypewriterOptions) {
  const [displayedText, setDisplayedText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const currentIndexRef = useRef(0)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // 如果禁用打字机效果，直接显示全部文本
    if (!enabled) {
      setDisplayedText(text)
      setIsTyping(false)
      return
    }

    // 重置状态
    setDisplayedText('')
    currentIndexRef.current = 0
    setIsTyping(true)

    // 清理之前的定时器
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }

    // 如果文本为空，直接返回
    if (!text) {
      setIsTyping(false)
      return
    }

    // 开始打字效果
    intervalRef.current = setInterval(() => {
      if (currentIndexRef.current < text.length) {
        setDisplayedText(text.slice(0, currentIndexRef.current + 1))
        currentIndexRef.current++
      } else {
        // 完成
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
        }
        setIsTyping(false)
        if (onComplete) {
          onComplete()
        }
      }
    }, speed)

    // 清理函数
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [text, speed, enabled, onComplete])

  // 跳过动画，直接显示全部文本
  const skip = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    setDisplayedText(text)
    setIsTyping(false)
    currentIndexRef.current = text.length
  }

  return {
    displayedText,
    isTyping,
    skip
  }
}
