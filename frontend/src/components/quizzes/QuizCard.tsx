'use client'

import { useState } from 'react'
import { Calendar, FileText, Loader2, MoreHorizontal, Trash2, Play, Eye } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Quiz } from '@/lib/types/quizzes'

/**
 * QuizCard Component
 * 
 * Displays individual quiz information with status badges and management options.
 * Supports different quiz types and provides quick actions.
 */
interface QuizCardProps {
  quiz: Quiz
  onDelete: (quizId: string) => Promise<unknown>
  onView: (quizId: string) => void  // 新增：查看测验
  onStart: (quizId: string) => void // 新增：开始测验
  deleting: boolean
}

export function QuizCard({ quiz, onDelete, onView, onStart, deleting }: QuizCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  /**
   * Maps quiz status to appropriate Badge variant
   * Note: Badge component only supports: 'default' | 'secondary' | 'destructive' | 'outline'
   */
  const getStatusVariant = (status: Quiz['status']) => {
    switch (status) {
      case 'running':
        return 'default' as const
      case 'completed':
        return 'default' as const  // Using 'default' instead of 'success'
      case 'failed':
        return 'destructive' as const
      case 'pending':
        return 'secondary' as const
      default:
        return 'outline' as const
    }
  }

  /**
   * Maps quiz status to appropriate CSS classes for custom styling
   */
  const getStatusClasses = (status: Quiz['status']) => {
    switch (status) {
      case 'running':
        return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'completed':
        return 'bg-green-50 text-green-700 border-green-200'  // Custom green styling
      case 'failed':
        return '' // Use destructive variant's default styling
      case 'pending':
        return '' // Use secondary variant's default styling
      default:
        return ''
    }
  }

  const getStatusText = (status: Quiz['status']) => {
    switch (status) {
      case 'running':
        return 'Generating'
      case 'completed':
        return 'Ready'
      case 'failed':
        return 'Failed'
      case 'pending':
        return 'Pending'
      default:
        return status
    }
  }

  const getTypeDisplayName = (type: string) => {
    const typeMap: Record<string, string> = {
      'multiple-choice': 'Multiple Choice',
      'true-false': 'True/False',
      'fill-blank': 'Fill in Blank',
      'mixed': 'Mixed Types',
    }
    return typeMap[type] || type
  }

  const handleDelete = async () => {
    await onDelete(quiz.id)
    setShowDeleteDialog(false)
  }

  const statusVariant = getStatusVariant(quiz.status)
  const statusClasses = getStatusClasses(quiz.status)

  return (
    <>
      <div className="rounded-lg border bg-card p-4 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between">
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold text-foreground hover:text-primary cursor-pointer" 
                  onClick={() => onView(quiz.id)}>
                {quiz.title}
              </h3>
              <Badge 
                variant={statusVariant}
                className={statusClasses}
              >
                {getStatusText(quiz.status)}
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <FileText className="h-4 w-4" />
                <span>{getTypeDisplayName(quiz.quiz_type)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                <span>
                  {new Date(quiz.created).toLocaleDateString()} at{' '}
                  {new Date(quiz.created).toLocaleTimeString()}
                </span>
              </div>
              <Badge variant="outline" className="text-xs">
                {quiz.question_count} questions
              </Badge>
            </div>

            {/* 新增：操作按钮 */}
            {quiz.status === 'completed' && (
              <div className="flex items-center gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onView(quiz.id)}
                  className="flex items-center gap-2"
                >
                  <Eye className="h-4 w-4" />
                  Preview
                </Button>
                <Button
                  size="sm"
                  onClick={() => onStart(quiz.id)}
                  className="flex items-center gap-2"
                >
                  <Play className="h-4 w-4" />
                  Start Quiz
                </Button>
              </div>
            )}

            {quiz.status === 'running' && (
              <div className="flex items-center gap-2 text-sm text-blue-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Generating questions...</span>
              </div>
            )}
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {/* 新增：查看选项 */}
              {quiz.status === 'completed' && (
                <DropdownMenuItem onClick={() => onView(quiz.id)}>
                  <Eye className="mr-2 h-4 w-4" />
                  View Quiz
                </DropdownMenuItem>
              )}
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => setShowDeleteDialog(true)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Quiz
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Quiz</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &ldquo;{quiz.title}&rdquo;? This action
              cannot be undone and the quiz will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete Quiz
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}