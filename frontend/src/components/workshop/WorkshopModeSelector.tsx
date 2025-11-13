'use client'

import { WorkshopTemplate } from '@/lib/types/workshop'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check } from 'lucide-react'

interface WorkshopModeSelectorProps {
  templates: WorkshopTemplate[]
  selectedTemplate: WorkshopTemplate | null
  onSelect: (template: WorkshopTemplate) => void
  isLoading?: boolean
}

export function WorkshopModeSelector({
  templates,
  selectedTemplate,
  onSelect,
  isLoading = false
}: WorkshopModeSelectorProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center text-muted-foreground">
          <div className="animate-pulse">Loading templates...</div>
        </div>
      </div>
    )
  }

  if (templates.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center text-muted-foreground">
          <p className="text-sm">No templates available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-muted-foreground">
        Select Thinking Workshop Mode
      </h3>

      <div className="grid grid-cols-1 gap-4">
        {templates.map((template) => (
          <Card
            key={template.mode_id}
            className={`cursor-pointer transition-all hover:shadow-md ${
              selectedTemplate?.mode_id === template.mode_id
                ? 'ring-2 ring-primary'
                : ''
            }`}
            onClick={() => onSelect(template)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{template.icon}</span>
                  <div>
                    <CardTitle className="text-base">{template.name}</CardTitle>
                    <p className="text-xs text-muted-foreground mt-1">
                      {template.description}
                    </p>
                  </div>
                </div>

                {selectedTemplate?.mode_id === template.mode_id && (
                  <div className="bg-primary text-primary-foreground rounded-full p-1">
                    <Check className="h-4 w-4" />
                  </div>
                )}
              </div>
            </CardHeader>

            <CardContent className="space-y-3">
              {/* Agent列表 */}
              <div>
                <p className="text-xs text-muted-foreground mb-2">Agents:</p>
                <div className="flex flex-wrap gap-2">
                  {template.agents.map((agent) => (
                    <Badge
                      key={agent.id}
                      variant="outline"
                      className="text-xs"
                      style={{ borderColor: agent.color }}
                    >
                      <span className="mr-1">{agent.avatar}</span>
                      {agent.name}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* 使用场景 */}
              <div>
                <p className="text-xs text-muted-foreground mb-2">Use Cases:</p>
                <div className="flex flex-wrap gap-1">
                  {template.use_cases.map((useCase, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {useCase}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* 预估时长 */}
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <span>⏱️</span>
                <span>Estimated Time: {template.estimated_time}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
