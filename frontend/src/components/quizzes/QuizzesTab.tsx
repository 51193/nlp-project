'use client'

import { useCallback, useState } from 'react'
import { AlertCircle, Loader2, RefreshCcw } from 'lucide-react'

import { useDeleteQuiz, useQuizzes } from '@/lib/hooks/use-quizzes'
import { QuizCard } from '@/components/quizzes/QuizCard'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { GenerateQuizDialog } from '@/components/quizzes/GenerateQuizDialog'
import { useRouter } from 'next/navigation'

const STATUS_ORDER: Array<{
  key: 'running' | 'completed' | 'failed' | 'pending'
  title: string
  description?: string
}> = [
  {
    key: 'running',
    title: 'Currently Generating',
    description: 'Quizzes that are actively being generated.',
  },
  {
    key: 'pending',
    title: 'Queued / Pending',
    description: 'Submitted quizzes waiting to start processing.',
  },
  {
    key: 'completed',
    title: 'Completed Quizzes',
    description: 'Ready to take, review, or share.',
  },
  {
    key: 'failed',
    title: 'Failed Quizzes',
    description: 'Quizzes that encountered issues during generation.',
  },
]

function SummaryBadge({ label, value }: { label: string; value: number }) {
  return (
    <Badge variant="outline" className="font-medium">
      <span className="text-muted-foreground mr-1.5">{label}</span>
      <span className="text-foreground">{value}</span>
    </Badge>
  )
}

/**
 * QuizzesTab Component
 * 
 * Displays a list of AI-generated quizzes with status filtering and management options.
 * Provides overview statistics and refresh functionality.
 */
export function QuizzesTab() {
  const [showGenerateDialog, setShowGenerateDialog] = useState(false)
  const router = useRouter() 
  const {
    quizzes,
    statusGroups,
    statusCounts,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuizzes()
  const deleteQuiz = useDeleteQuiz()

  const handleRefresh = useCallback(() => {
    void refetch()
  }, [refetch])

  const handleDelete = useCallback(
    (quizId: string) => deleteQuiz.mutateAsync(quizId),
    [deleteQuiz]
  )

    const handleViewQuiz = useCallback((quizId: string) => {
    console.log('Navigating to quiz:', quizId) // 添加日志
    router.push(`/quiz/${quizId}/preview`)
    }, [router])

    const handleStartQuiz = useCallback((quizId: string) => {
    console.log('Starting quiz:', quizId) // 添加日志
    router.push(`/quiz/${quizId}/take`)
    }, [router])
    
  const emptyState = !isLoading && quizzes.length === 0

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">Quiz Overview</h2>
          <p className="text-sm text-muted-foreground">
            Monitor quiz generation and review the final assessments.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowGenerateDialog(true)}>
            Generate Quiz
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isFetching}
          >
            {isFetching ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCcw className="mr-2 h-4 w-4" />
            )}
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <SummaryBadge label="Total" value={statusCounts.total} />
        <SummaryBadge label="Generating" value={statusCounts.running} />
        <SummaryBadge label="Completed" value={statusCounts.completed} />
        <SummaryBadge label="Failed" value={statusCounts.failed} />
        <SummaryBadge label="Pending" value={statusCounts.pending} />
      </div>

      {isError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load quizzes</AlertTitle>
          <AlertDescription>
            We could not fetch the latest quizzes. Try again shortly.
          </AlertDescription>
        </Alert>
      ) : null}

      {isLoading ? (
        <div className="flex items-center gap-3 rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading quizzes…
        </div>
      ) : null}

      {emptyState ? (
        <div className="rounded-lg border border-dashed bg-muted/30 p-10 text-center">
          <p className="text-sm text-muted-foreground">
            No quizzes generated yet. Create your first quiz from notebook content.
          </p>
        </div>
      ) : null}

      {STATUS_ORDER.map(({ key, title, description }) => {
        const data = statusGroups[key]
        if (!data || data.length === 0) {
          return null
        }

        return (
          <section key={key} className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold leading-tight">{title}</h3>
              {description ? (
                <p className="text-sm text-muted-foreground">{description}</p>
              ) : null}
            </div>
            <Separator />
            <div className="space-y-4">
              {data.map((quiz) => (
                <QuizCard
                  key={quiz.id}
                  quiz={quiz}
                  onDelete={handleDelete}
                  deleting={deleteQuiz.isPending}
                  onView={handleViewQuiz}
                  onStart={handleStartQuiz}
                />
              ))}
            </div>
          </section>
        )
      })}

      <GenerateQuizDialog
        open={showGenerateDialog}
        onOpenChange={setShowGenerateDialog}
      />
    </div>
  )
}