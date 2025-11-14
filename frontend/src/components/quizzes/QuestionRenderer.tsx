'use client'

import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { QuizQuestion } from '@/lib/types/quizzes'

interface QuestionRendererProps {
  question: QuizQuestion
  userAnswer?: string
  onAnswerChange?: (answer: string) => void
  showAnswers?: boolean
  disabled?: boolean
}

/**
 * Universal Question Renderer Component
 * 
 * Handles all question types based on the existing type definitions
 */
export function QuestionRenderer({ 
  question, 
  userAnswer, 
  onAnswerChange, 
  showAnswers = false,
  disabled = false 
}: QuestionRendererProps) {
  const handleAnswerChange = (value: string) => {
    onAnswerChange?.(value)
  }

  // Render based on question type
  switch (question.type) {
    case 'multiple-choice':
      return (
        <div className="space-y-4">
          <div className="text-base font-medium">{question.question}</div>
          <RadioGroup 
            value={userAnswer} 
            onValueChange={handleAnswerChange}
            disabled={disabled}
            className="space-y-3"
          >
            {question.options?.map((option, index) => (
              <div key={index} className="flex items-center space-x-3">
                <RadioGroupItem 
                  value={option} 
                  id={`${question.id}-option-${index}`}
                />
                <Label 
                  htmlFor={`${question.id}-option-${index}`}
                  className="flex-1 cursor-pointer"
                >
                  {option}
                </Label>
              </div>
            ))}
          </RadioGroup>
          {showAnswers && question.explanation && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-blue-900 mb-1">Explanation</p>
              <p className="text-sm text-blue-700">{question.explanation}</p>
            </div>
          )}
        </div>
      )

    case 'true-false':
      return (
        <div className="space-y-4">
          <div className="text-base font-medium">{question.question}</div>
          <RadioGroup 
            value={userAnswer} 
            onValueChange={handleAnswerChange}
            disabled={disabled}
            className="space-y-3"
          >
            {['True', 'False'].map((option) => (
              <div key={option} className="flex items-center space-x-3">
                <RadioGroupItem 
                  value={option} 
                  id={`${question.id}-${option}`}
                />
                <Label 
                  htmlFor={`${question.id}-${option}`}
                  className="flex-1 cursor-pointer"
                >
                  {option}
                </Label>
              </div>
            ))}
          </RadioGroup>
          {showAnswers && question.explanation && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-blue-900 mb-1">Explanation</p>
              <p className="text-sm text-blue-700">{question.explanation}</p>
            </div>
          )}
        </div>
      )

    case 'fill-blank':
      return (
        <div className="space-y-4">
          <div className="text-base font-medium">{question.question}</div>
          <Input
            value={userAnswer || ''}
            onChange={(e) => handleAnswerChange(e.target.value)}
            placeholder="Type your answer here..."
            disabled={disabled}
            className={showAnswers ? (userAnswer === question.correct_answer ? 'border-green-500' : 'border-red-500') : ''}
          />
          {showAnswers && question.explanation && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-blue-900 mb-1">Explanation</p>
              <p className="text-sm text-blue-700">{question.explanation}</p>
            </div>
          )}
        </div>
      )

    case 'problem-solving':
      return (
        <div className="space-y-4">
          <div className="text-base font-medium">{question.question}</div>
          <Textarea
            value={userAnswer || ''}
            onChange={(e) => handleAnswerChange(e.target.value)}
            placeholder="Explain your solution..."
            disabled={disabled}
            rows={4}
          />
          {showAnswers && question.explanation && (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-blue-900 mb-1">Explanation</p>
              <p className="text-sm text-blue-700">{question.explanation}</p>
            </div>
          )}
        </div>
      )

    default:
      return (
        <div className="space-y-4">
          <div className="text-base font-medium">{question.question}</div>
          <p className="text-sm text-muted-foreground">Unsupported question type: {question.type}</p>
        </div>
      )
  }
}