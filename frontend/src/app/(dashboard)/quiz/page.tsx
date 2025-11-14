'use client'

import { useState } from 'react'

import { AppShell } from '@/components/layout/AppShell'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { QuizzesTab } from '@/components/quizzes/QuizzesTab'
import { TemplatesTab } from '@/components/quizzes/TemplatesTab'
import { FileText, LayoutTemplate } from 'lucide-react'

/**
 * Quizzes Page Component
 * 
 * Main page for managing AI-generated quizzes based on notebook content.
 * Provides two tab views: generated quizzes and quiz templates.
 */
export default function QuizzesPage() {
  const [activeTab, setActiveTab] = useState<'quizzes' | 'templates'>('quizzes')

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-6 space-y-6">
          <header className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Quizzes</h1>
            <p className="text-muted-foreground">
              Generate and manage AI-powered quizzes based on your notebook content. 
              Test your knowledge with intelligent question sets.
            </p>
          </header>

          <Tabs
            value={activeTab}
            onValueChange={(value) => setActiveTab(value as 'quizzes' | 'templates')}
            className="space-y-6"
          >
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Options</p>
              <TabsList aria-label="Quiz views" className="w-full max-w-md">
                <TabsTrigger value="quizzes">
                  <FileText className="h-4 w-4" />
                  Generated Quizzes
                </TabsTrigger>
                <TabsTrigger value="templates">
                  <LayoutTemplate className="h-4 w-4" />
                  Quiz Templates
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="quizzes">
              <QuizzesTab />
            </TabsContent>

            <TabsContent value="templates">
              <TemplatesTab />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </AppShell>
  )
}