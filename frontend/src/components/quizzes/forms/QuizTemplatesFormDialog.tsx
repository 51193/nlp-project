'use client'

import { useCallback, useEffect } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { QuizTemplate } from '@/lib/types/quizzes'
import {
  useCreateQuizTemplate,
  useUpdateQuizTemplate,
} from '@/lib/hooks/use-quizzes'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'

/**
 * Validation schema for quiz template form
 */
const quizTemplateSchema = z.object({
  name: z.string().min(1, 'Template name is required'),
  description: z.string().optional(),
  quiz_type: z.string().min(1, 'Quiz type is required'),
  default_question_count: z.number()
    .int('Must be an integer')
    .min(1, 'At least 1 question')
    .max(50, 'Maximum 50 questions'),
  difficulty_level: z.string()
    .min(1, 'Difficulty level is required')
    .refine((val) => ['easy', 'medium', 'hard'].includes(val), {
      message: 'Difficulty level must be one of: easy, medium, hard'
    }),
  instructions: z.string().min(1, 'Default instructions are required'),
})

export type QuizTemplateFormValues = z.infer<typeof quizTemplateSchema>

interface QuizTemplateFormDialogProps {
  mode: 'create' | 'edit'
  open: boolean
  onOpenChange: (open: boolean) => void
  initialData?: QuizTemplate
}

/**
 * QuizTemplateFormDialog Component
 * 
 * Provides form interface for creating and editing quiz templates.
 * Includes validation and submission handling for template configuration.
 */
export function QuizTemplateFormDialog({
  mode,
  open,
  onOpenChange,
  initialData,
}: QuizTemplateFormDialogProps) {
  const createTemplate = useCreateQuizTemplate()
  const updateTemplate = useUpdateQuizTemplate()

  /**
   * Available quiz types for selection
   */
  const quizTypes = [
    { value: 'multiple-choice', label: 'Multiple Choice' },
    { value: 'true-false', label: 'True/False' },
    { value: 'fill-blank', label: 'Fill in Blank' },
    { value: 'mixed', label: 'Mixed Types' },
  ]

  /**
   * Available difficulty levels for selection
   */
  const difficultyLevels = [
    { value: 'easy', label: 'Easy' },
    { value: 'medium', label: 'Medium' },
    { value: 'hard', label: 'Hard' },
  ]

  /**
   * Gets default form values based on mode and initial data
   */
  const getDefaults = useCallback((): QuizTemplateFormValues => {
    if (initialData) {
      return {
        name: initialData.name,
        description: initialData.description ?? '',
        quiz_type: initialData.quiz_type,
        default_question_count: initialData.default_question_count,
        difficulty_level: initialData.difficulty_level,
        instructions: initialData.instructions,
      }
    }

    return {
      name: '',
      description: '',
      quiz_type: 'multiple-choice',
      default_question_count: 10,
      difficulty_level: 'medium',
      instructions: 'Please answer the following questions based on the provided content.',
    }
  }, [initialData])

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<QuizTemplateFormValues>({
    resolver: zodResolver(quizTemplateSchema),
    defaultValues: getDefaults(),
  })

  /**
   * Reset form when dialog opens/closes
   */
  useEffect(() => {
    if (!open) {
      return
    }
    reset(getDefaults())
  }, [open, reset, getDefaults])

  /**
   * Handles form submission for both create and edit modes
   */
  const onSubmit = async (values: QuizTemplateFormValues) => {
  const payload = {
    ...values,
    description: values.description ?? '',
    difficulty_level: values.difficulty_level as 'easy' | 'medium' | 'hard',
  }

  if (mode === 'create') {
    await createTemplate.mutateAsync(payload)
  } else if (initialData) {
    await updateTemplate.mutateAsync({
      templateId: initialData.id,
      payload,
    })
  }

  onOpenChange(false)
}

  const isSubmitting = createTemplate.isPending || updateTemplate.isPending
  const isEdit = mode === 'edit'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? 'Edit Quiz Template' : 'Create Quiz Template'}
          </DialogTitle>
          <DialogDescription>
            Define reusable configurations for quiz generation, including question types, 
            difficulty levels, and default instructions.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 pt-2">
          {/* Basic Information Section */}
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Basic Information
              </h3>
              <Separator className="mt-2" />
            </div>
            
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Template Name *</Label>
                <Input 
                  id="name" 
                  placeholder="e.g., Quick Knowledge Check"
                  {...register('name')} 
                />
                {errors.name ? (
                  <p className="text-xs text-red-600">{errors.name.message}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="default_question_count">Default Question Count *</Label>
                <Input
                  id="default_question_count"
                  type="number"
                  min={1}
                  max={50}
                  {...register('default_question_count', { valueAsNumber: true })}
                />
                {errors.default_question_count ? (
                  <p className="text-xs text-red-600">{errors.default_question_count.message}</p>
                ) : null}
              </div>

              <div className="md:col-span-2 space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  rows={2}
                  placeholder="Brief description of when to use this template..."
                  {...register('description')}
                />
              </div>
            </div>
          </div>

          {/* Quiz Configuration Section */}
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Quiz Configuration
              </h3>
              <Separator className="mt-2" />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Controller
                control={control}
                name="quiz_type"
                render={({ field }) => (
                  <div className="space-y-2">
                    <Label>Quiz Type *</Label>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select quiz type" />
                      </SelectTrigger>
                      <SelectContent>
                        {quizTypes.map((type) => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.quiz_type ? (
                      <p className="text-xs text-red-600">{errors.quiz_type.message}</p>
                    ) : null}
                  </div>
                )}
              />

              <Controller
                control={control}
                name="difficulty_level"
                render={({ field }) => (
                  <div className="space-y-2">
                    <Label>Difficulty Level *</Label>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select difficulty" />
                      </SelectTrigger>
                      <SelectContent>
                        {difficultyLevels.map((level) => (
                          <SelectItem key={level.value} value={level.value}>
                            {level.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.difficulty_level ? (
                      <p className="text-xs text-red-600">{errors.difficulty_level.message}</p>
                    ) : null}
                  </div>
                )}
              />
            </div>
          </div>

          {/* Instructions Section */}
          <div className="space-y-2">
            <Label htmlFor="instructions">Default Instructions *</Label>
            <Textarea
              id="instructions"
              rows={4}
              placeholder="Provide clear instructions for users taking quizzes generated with this template..."
              {...register('instructions')}
            />
            {errors.instructions ? (
              <p className="text-xs text-red-600">{errors.instructions.message}</p>
            ) : null}
            <p className="text-xs text-muted-foreground">
              These instructions will be displayed to users at the beginning of each quiz.
            </p>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? isEdit
                  ? 'Saving…'
                  : 'Creating…'
                : isEdit
                  ? 'Save Changes'
                  : 'Create Template'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}