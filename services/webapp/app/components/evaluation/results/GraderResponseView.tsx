import { useState, useMemo } from 'react';
import { GraderGradingState } from './GraderGradingState';
import { GraderErrorState } from './GraderErrorState';
import { GraderSuccessState } from './GraderSuccessState';

interface GraderResponse {
  score: number;
  reasoning: string;
  criteria_scores?: {
    helpfulness?: number;
    accuracy?: number;
    completeness?: number;
    tone?: number;
  };
}

interface GraderResponseViewProps {
  response: string;
}


// Utility function to extract JSON from markdown code blocks
function extractJsonFromMarkdown(text: string): string {
  // Check for ```json code block
  const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/);
  if (jsonMatch) {
    return jsonMatch[1];
  }
  // Check for plain ``` code block
  const codeMatch = text.match(/```\n([\s\S]*?)\n```/);
  if (codeMatch) {
    return codeMatch[1];
  }
  // Return original if no code block found
  return text;
}

export function GraderResponseView({ response }: GraderResponseViewProps) {
  const [showFullReasoning, setShowFullReasoning] = useState(false);
  
  const isGrading = response === null || response === '';
  
  const parsedResponse = useMemo<GraderResponse | null>(() => {
    
    if (!response) return null;
    
    try {
      // First, check if the response is wrapped in an outer JSON object
      let innerResponse = response;
      try {
        const outerParsed = JSON.parse(response);
        // If it has a "response" field, that's the actual grader response
        if (outerParsed.response) {
          innerResponse = outerParsed.response;
        }
      } catch {
        // Not wrapped in outer JSON, use as-is
      }
      
      // Extract JSON from markdown if present
      const cleanJson = extractJsonFromMarkdown(innerResponse.trim());
      const parsed = JSON.parse(cleanJson);
      return {
        score: parsed.score || 0,
        reasoning: parsed.reasoning || '',
        criteria_scores: parsed.criteria_scores || {}
      };
    } catch (err) {
      console.error('Failed to parse grader response:', err);
      console.error('Original response:', response);
      return null;
    }
  }, [response]);

  // Show grading in progress animation
  if (isGrading) {
    return <GraderGradingState />;
  }

  // Show failed to parse state
  if (!parsedResponse) {
    return <GraderErrorState response={response} />;
  }

  // Show success state
  return (
    <GraderSuccessState 
      parsedResponse={parsedResponse}
      showFullReasoning={showFullReasoning}
      onToggleReasoning={() => setShowFullReasoning(!showFullReasoning)}
    />
  );
}