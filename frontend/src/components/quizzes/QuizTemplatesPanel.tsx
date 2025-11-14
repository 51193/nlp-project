'use client'

import { useMemo, useState } from 'react'
import { Copy, Edit3, MoreVertical, Trash2, FileText, Clock } from 'lucide-react'

import { QuizTemplate } from '@/lib/types/quizzes'
import {
  useDeleteQuizTemplate,
  useDuplicateQuizTemplate,
} from '@/lib/hooks/use-quizzes'
import { QuizTemplateFormDialog } from '@/components/quizzes/forms/QuizTemplatesFormDialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface QuizTemplatesPanelProps {
  quizTemplates: QuizTemplate[]
}

/**
 * QuizTemplatesPanel Component
 * 
 * Displays and manages quiz templates with full CRUD operations.
 * Provides interface for creating, editing, duplicating, and deleting quiz templates.
 */
export function QuizTemplatesPanel({
  quizTemplates,
}: QuizTemplatesPanelProps) {
  const [createOpen, setCreateOpen] = useState(false)
  const [editTemplate, setEditTemplate] = useState<QuizTemplate | null>(null)

  const deleteTemplate = useDeleteQuizTemplate()
  const duplicateTemplate = useDuplicateQuizTemplate()

  const sortedTemplates = useMemo(
    () =>
      [...quizTemplates].sort((a, b) => a.name.localeCompare(b.name, 'en')),
    [quizTemplates]
  )

  /**
   * Maps difficulty level to appropriate badge styling
   */
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'hard':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  /**
   * Maps quiz type to human-readable display name
   */
  const getTypeDisplayName = (type: string) => {
    const typeMap: Record<string, string> = {
      'multiple-choice': 'Multiple Choice',
      'true-false': 'True/False',
      'fill-blank': 'Fill in Blank',
      'mixed': 'Mixed Types',
    }
    return typeMap[type] || type
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Quiz Templates</h2>
          <p className="text-sm text-muted-foreground">
            Define reusable configurations for different assessment types and difficulty levels.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          Create Template
        </Button>
      </div>

      {sortedTemplates.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-muted/30 p-10 text-center text-sm text-muted-foreground">
          <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium mb-2">No quiz templates yet</p>
          <p>Create your first template to streamline assessment generation.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedTemplates.map((template) => (
            <Card key={template.id} className="shadow-sm">
              <CardHeader className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-lg font-semibold">
                      {template.name}
                    </CardTitle>
                    <Badge 
                      variant="outline" 
                      className={getDifficultyColor(template.difficulty_level)}
                    >
                      {template.difficulty_level}
                    </Badge>
                  </div>
                  <CardDescription className="text-sm text-muted-foreground">
                    {template.description || 'No description provided.'}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setEditTemplate(template)}
                  >
                    <Edit3 className="mr-2 h-4 w-4" /> Edit
                  </Button>
                  <AlertDialog>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent
                        align="end"
                        className="w-44"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <DropdownMenuItem
                          onClick={() => duplicateTemplate.mutate(template.id)}
                          disabled={duplicateTemplate.isPending}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <AlertDialogTrigger asChild>
                          <DropdownMenuItem className="text-destructive focus:text-destructive">
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </AlertDialogTrigger>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete template?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will permanently remove "{template.name}". 
                          Existing quizzes will not be affected, but new ones can no longer use this template.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => deleteTemplate.mutate(template.id)}
                          disabled={deleteTemplate.isPending}
                        >
                          {deleteTemplate.isPending ? 'Deleting…' : 'Delete'}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 text-sm">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Quiz Type
                    </p>
                    <div className="flex items-center gap-2 text-foreground">
                      <FileText className="h-4 w-4" />
                      <span>{getTypeDisplayName(template.quiz_type)}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Question Count
                    </p>
                    <p className="text-foreground">{template.default_question_count} questions</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Difficulty
                    </p>
                    <Badge 
                      variant="outline" 
                      className={getDifficultyColor(template.difficulty_level)}
                    >
                      {template.difficulty_level}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Last Updated
                    </p>
                    <div className="flex items-center gap-2 text-foreground">
                      <Clock className="h-4 w-4" />
                      <span>{new Date(template.updated).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                {template.instructions ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Default Instructions
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-muted-foreground">
                      {template.instructions}
                    </p>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <QuizTemplateFormDialog
        mode="create"
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      <QuizTemplateFormDialog
        mode="edit"
        open={Boolean(editTemplate)}
        onOpenChange={(open: boolean) => {
            if (!open) {
            setEditTemplate(null)
            }
        }}
        initialData={editTemplate ?? undefined}
      />
    </div>
  )
}