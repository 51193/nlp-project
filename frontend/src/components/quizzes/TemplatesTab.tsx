'use client'

import { useMemo } from 'react'
import { AlertCircle, Lightbulb, Loader2 } from 'lucide-react'

import { QuizTemplatesPanel } from '@/components/quizzes/QuizTemplatesPanel'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useQuizTemplates } from '@/lib/hooks/use-quizzes'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

/**
 * TemplatesTab Component for Quizzes
 * 
 * Provides a workspace for managing reusable quiz templates and configurations.
 * Allows users to create, edit, and organize quiz templates for efficient assessment generation.
 */
export function TemplatesTab() {
  const {
    quizTemplates,
    isLoading: loadingQuizTemplates,
    error: quizTemplatesError,
  } = useQuizTemplates()

  const isLoading = loadingQuizTemplates
  const hasError = quizTemplatesError

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">Quiz Templates Workspace</h2>
        <p className="text-sm text-muted-foreground">
          Build reusable quiz configurations for efficient and consistent assessment generation.
        </p>
      </div>

      <Accordion type="single" collapsible className="w-full">
        <AccordionItem 
          value="overview" 
          className="overflow-hidden rounded-xl border border-border bg-muted/40 px-4"
        >
          <AccordionTrigger className="gap-2 py-4 text-left text-sm font-semibold">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-primary" />
              How quiz templates streamline assessment creation
            </div>
          </AccordionTrigger>
          <AccordionContent className="text-sm text-muted-foreground">
            <div className="space-y-4">
              <p className="text-muted-foreground/90">
                Quiz templates provide standardized configurations for different assessment types, 
                ensuring consistency and saving time when generating new quizzes from your notebook content.
              </p>

              <div className="space-y-2">
                <h4 className="font-medium text-foreground">Template configurations</h4>
                <ul className="list-disc space-y-1 pl-5">
                  <li>Define quiz types: multiple choice, true/false, fill-in-blank, or mixed formats</li>
                  <li>Set default question counts and difficulty levels</li>
                  <li>Store standard instructions and assessment criteria</li>
                  <li>Configure time limits and scoring systems</li>
                </ul>
              </div>

              <div className="space-y-2">
                <h4 className="font-medium text-foreground">Content adaptation</h4>
                <ul className="list-disc space-y-1 pl-5">
                  <li>Templates intelligently adapt to your notebook content</li>
                  <li>Maintain consistent question quality across different topics</li>
                  <li>Ensure appropriate difficulty based on source material complexity</li>
                  <li>Generate contextually relevant assessment questions</li>
                </ul>
              </div>

              <div className="space-y-2">
                <h4 className="font-medium text-foreground">Recommended workflow</h4>
                <ol className="list-decimal space-y-1 pl-5">
                  <li>Create templates for different assessment types and difficulty levels</li>
                  <li>Organize templates by subject area or learning objectives</li>
                  <li>Select the appropriate template when generating quizzes from notebook content</li>
                  <li>Review and customize generated questions as needed</li>
                </ol>
                <p className="text-xs text-muted-foreground/80">
                  Well-designed templates ensure consistent assessment quality and reduce 
                  manual configuration time for each new quiz.
                </p>
              </div>

              <div className="rounded-lg bg-blue-50 p-4 border border-blue-200">
                <h4 className="font-medium text-blue-900 mb-2">Best Practices</h4>
                <ul className="list-disc space-y-1 pl-5 text-blue-800 text-sm">
                  <li>Create separate templates for formative vs. summative assessments</li>
                  <li>Design templates with specific learning objectives in mind</li>
                  <li>Include clear instructions and scoring rubrics in template descriptions</li>
                  <li>Test templates with different notebook content to ensure adaptability</li>
                </ul>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {hasError ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load quiz templates</AlertTitle>
          <AlertDescription>
            {quizTemplatesError?.message || 'Ensure the API is running and try again. Quiz templates may be unavailable.'}
          </AlertDescription>
        </Alert>
      ) : null}

      {isLoading ? (
        <div className="flex items-center gap-3 rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading quiz templates…
        </div>
      ) : (
        <div className="grid gap-6">
          <QuizTemplatesPanel
            quizTemplates={quizTemplates}
          />
        </div>
      )}
    </div>
  )
}