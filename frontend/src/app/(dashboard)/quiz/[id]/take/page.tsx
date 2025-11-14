'use client'

import { use, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { QuestionRenderer } from '@/components/quizzes/QuestionRenderer'
import { useQuiz } from '@/lib/hooks/use-quizzes'
import { useParams } from 'next/navigation'

interface QuizTakePageProps {
  params: Promise<{ quizId: string }>
}

export default function QuizTakePage() {
  // const { quizId } = use(params)
  const router = useRouter()
  const params = useParams()
  const quizId = params.id as string
  const { data: quiz, isLoading, error } = useQuiz(quizId)
  
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({})
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)

  const handleBack = () => {
    router.push('/quiz')
  }

  const handleAnswerChange = (questionId: string, answer: string) => {
    setUserAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }))
  }

  const handleSubmit = () => {
    setIsSubmitted(true)
  }

  const handleReset = () => {
    setUserAnswers({})
    setIsSubmitted(false)
    setCurrentQuestionIndex(0)
  }

  const calculateScore = () => {
    if (!quiz?.questions) return 0
    
    let correctCount = 0
    quiz.questions.forEach(question => {
      const userAnswer = userAnswers[question.id]
      if (userAnswer === question.correct_answer) {
        correctCount++
      }
    })
    
    return Math.round((correctCount / quiz.questions.length) * 100)
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

  const currentQuestion = quiz.questions?.[currentQuestionIndex]
  const score = calculateScore()
  const allQuestionsAnswered = quiz.questions?.every(q => userAnswers[q.id])

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
                  {isSubmitted ? 'Quiz Results' : 'Test your knowledge'}
                </p>
              </div>
            </div>
            
            {!isSubmitted && (
              <div className="flex items-center gap-4">
                <Badge variant="outline">
                  Question {currentQuestionIndex + 1} of {quiz.questions?.length || 0}
                </Badge>
                <Button 
                  onClick={handleSubmit}
                  disabled={!allQuestionsAnswered}
                >
                  Submit Quiz
                </Button>
              </div>
            )}
          </div>

          {/* Progress and Score */}
          {isSubmitted && (
            <Card className="bg-primary/5 border-primary/20">
              <CardContent className="p-6">
                <div className="text-center">
                  <h3 className="text-2xl font-bold mb-2">Quiz Complete!</h3>
                  <p className="text-4xl font-bold text-primary mb-4">{score}%</p>
                  <p className="text-muted-foreground mb-4">
                    You got {Object.keys(userAnswers).filter(id => {
                      const question = quiz.questions?.find(q => q.id === id)
                      return question && userAnswers[id] === question.correct_answer
                    }).length} out of {quiz.questions?.length || 0} questions correct
                  </p>
                  <div className="flex gap-2 justify-center">
                    <Button variant="outline" onClick={handleReset}>
                      Try Again
                    </Button>
                    <Button onClick={handleBack}>
                      Back to Quizzes
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Question Navigation */}
          {!isSubmitted && quiz.questions && quiz.questions.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {quiz.questions.map((_, index) => (
                <Button
                  key={index}
                  variant={currentQuestionIndex === index ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCurrentQuestionIndex(index)}
                >
                  {index + 1}
                </Button>
              ))}
            </div>
          )}

          {/* Current Question */}
          {currentQuestion && !isSubmitted && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-start justify-between">
                  <span>Question {currentQuestionIndex + 1}</span>
                  <div className="flex gap-2">
                    <Badge variant="outline" className="text-xs">
                      {currentQuestion.difficulty}
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      {currentQuestion.type}
                    </Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <QuestionRenderer 
                  question={currentQuestion}
                  userAnswer={userAnswers[currentQuestion.id]}
                  onAnswerChange={(answer) => handleAnswerChange(currentQuestion.id, answer)}
                  showAnswers={false}
                  disabled={false}
                />
              </CardContent>
            </Card>
          )}

          {/* Results Review */}
          {isSubmitted && quiz.questions && (
            <div className="space-y-6">
              {quiz.questions.map((question, index) => {
                const userAnswer = userAnswers[question.id]
                const isCorrect = userAnswer === question.correct_answer
                
                return (
                  <Card key={question.id} className={isCorrect ? 'border-green-200' : 'border-red-200'}>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-start justify-between">
                        <span>Question {index + 1}</span>
                        <div className="flex items-center gap-2">
                          {isCorrect ? (
                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                          ) : (
                            <XCircle className="h-5 w-5 text-red-600" />
                          )}
                          <Badge variant={isCorrect ? "default" : "destructive"} className="text-xs">
                            {isCorrect ? 'Correct' : 'Incorrect'}
                          </Badge>
                        </div>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <QuestionRenderer 
                        question={question}
                        userAnswer={userAnswer}
                        showAnswers={true}
                        disabled={true}
                      />
                      {!isCorrect && (
                        <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-200">
                          <p className="text-sm font-medium text-red-900">
                            Your answer: {userAnswer || 'No answer provided'}
                          </p>
                          <p className="text-sm font-medium text-green-900 mt-1">
                            Correct answer: {question.correct_answer}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}