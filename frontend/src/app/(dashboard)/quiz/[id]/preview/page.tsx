'use client'

import { use } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, FileText } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { QuestionRenderer } from '@/components/quizzes/QuestionRenderer'
import { useQuiz } from '@/lib/hooks/use-quizzes'
import { QuizStatus } from '@/lib/types/quizzes'
import { useParams } from 'next/navigation'

interface QuizPreviewPageProps {
  params: Promise<{ quizId: string }>
}

export default function QuizPreviewPage() {
//   const { quizId } = use(params)
  const params = useParams()
  const quizId = params.id as string
  const router = useRouter()
  const { data: quiz, isLoading, error } = useQuiz(quizId)

  const handleBack = () => {
    router.push('/quiz')
  }

  const handleStartQuiz = () => {
    router.push(`/quiz/${quizId}/take`)
  }

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex h-full items-center justify-center p-8">
          <LoadingSpinner />
        </div>
      </AppShell>
    )
  }

  if (error || !quiz) {
    return (
      <AppShell>
        <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
          <Alert variant="destructive" className="max-w-md">
            <AlertTitle>Failed to load quiz</AlertTitle>
            <AlertDescription>
              {error ? error.message : 'Quiz not found'}
            </AlertDescription>
          </Alert>
          <Button onClick={handleBack} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Quizzes
          </Button>
        </div>
      </AppShell>
    )
  }

  // 使用您现有的 QuizStatus 类型
  if (quiz.status !== 'completed') {
    return (
      <AppShell>
        <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
          <Alert className="max-w-md">
            <AlertTitle>Quiz Not Ready</AlertTitle>
            <AlertDescription>
              This quiz is still {quiz.status}. Please check back later.
            </AlertDescription>
          </Alert>
          <Button onClick={handleBack} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Quizzes
          </Button>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="outline" size="sm" onClick={handleBack}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">{quiz.title}</h1>
                <p className="text-muted-foreground">
                  Preview questions before starting the quiz
                </p>
              </div>
            </div>
            <Button onClick={handleStartQuiz}>
              Start Quiz
            </Button>
          </div>

          {/* Quiz Info */}
          <div className="flex flex-wrap gap-4">
            <Badge variant="outline" className="flex items-center gap-2">
              <FileText className="h-3 w-3" />
              {quiz.question_count} questions
            </Badge>
            <Badge variant="outline">
              {quiz.quiz_type === 'multiple-choice' ? 'Multiple Choice' : 
               quiz.quiz_type === 'true-false' ? 'True/False' :
               quiz.quiz_type === 'fill-blank' ? 'Fill in Blank' :
               quiz.quiz_type === 'problem-solving' ? 'Problem Solving' : 
               quiz.quiz_type}
            </Badge>
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              Ready
            </Badge>
          </div>

          {/* Questions - Preview Mode (no answers) */}
          <div className="space-y-6">
            {quiz.questions?.map((question, index) => (
              <Card key={question.id} className="bg-muted/30">
                <CardHeader>
                  <CardTitle className="text-lg flex items-start justify-between">
                    <span>Question {index + 1}</span>
                    <div className="flex gap-2">
                      <Badge variant="outline" className="text-xs">
                        {question.difficulty}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {question.type}
                      </Badge>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <QuestionRenderer 
                    question={question} 
                    disabled={true} // Preview mode is read-only
                    showAnswers={false} // Don't show answers in preview
                  />
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Start Quiz CTA */}
          <Card className="bg-primary/5 border-primary/20">
            <CardContent className="p-6 text-center">
              <h3 className="text-lg font-semibold mb-2">Ready to test your knowledge?</h3>
              <p className="text-muted-foreground mb-4">
                Start the quiz to answer these questions and get scored.
              </p>
              <Button size="lg" onClick={handleStartQuiz}>
                Start Quiz Now
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}