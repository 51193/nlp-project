import { FileText } from 'lucide-react'

interface GeneratedQuizzesTabProps {
  // Props can be added here as needed
}

/**
 * Displays a list of AI-generated quizzes from notebook content
 * Allows users to take quizzes, view results, and manage generated content
 */
export function GeneratedQuizzesTab({}: GeneratedQuizzesTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Generated Quizzes</h2>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors">
          Generate New Quiz
        </button>
      </div>
      
      <div className="border rounded-lg p-6 text-center">
        <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-lg font-medium mb-2">No quizzes generated yet</h3>
        <p className="text-muted-foreground mb-4">
          Generate your first quiz from notebook content to test your knowledge
        </p>
      </div>
    </div>
  )
}