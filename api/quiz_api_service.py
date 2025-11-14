"""
Quiz service layer using API client.
This replaces direct HTTP calls in the frontend components.
Provides a clean interface for quiz-related operations.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from api.client import api_client


class QuizAPIService:
    """Service layer for quiz operations using API client."""

    def __init__(self):
        logger.info("Using API client for quiz operations")

    # Quiz methods
    def get_quizzes(self) -> List[Dict[Any, Any]]:
        """Get all quizzes."""
        try:
            result = api_client._make_request("GET", "/api/quizzes")
            return result if isinstance(result, list) else [result]
        except Exception as e:
            logger.error(f"Failed to get quizzes: {e}")
            return []

    def get_quiz(self, quiz_id: str) -> Optional[Dict[Any, Any]]:
        """Get a specific quiz by ID."""
        try:
            return api_client._make_request("GET", f"/api/quizzes/{quiz_id}")
        except Exception as e:
            logger.error(f"Failed to get quiz {quiz_id}: {e}")
            return None

    def generate_quiz(self, quiz_data: Dict) -> Optional[Dict[Any, Any]]:
        """
        Generate a new quiz.
        
        Args:
            quiz_data: Dictionary containing quiz generation parameters
                - quiz_profile: str (required)
                - quiz_title: str (required) 
                - content: str (required)
                - quiz_template: Optional[str]
                - notebook_id: Optional[str]
                - source_ids: List[str]
                - note_ids: List[str]
                - question_count: int
                - quiz_type: str
                - difficulty: str
        """
        try:
            return api_client._make_request("POST", "/api/quizzes/generate", json=quiz_data)
        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}")
            return None

    def submit_quiz_answers(self, quiz_id: str, answers: Dict, time_spent_seconds: Optional[int] = None) -> Optional[Dict[Any, Any]]:
        """
        Submit answers for a quiz and get scoring results.
        
        Args:
            quiz_id: ID of the quiz to submit
            answers: Dictionary mapping question IDs to user answers
            time_spent_seconds: Optional time spent on the quiz
        """
        try:
            data = {
                "answers": answers,
                "time_spent_seconds": time_spent_seconds
            }
            return api_client._make_request("POST", f"/api/quizzes/{quiz_id}/submit", json=data)
        except Exception as e:
            logger.error(f"Failed to submit quiz answers: {e}")
            return None

    def delete_quiz(self, quiz_id: str) -> bool:
        """Delete a quiz."""
        try:
            api_client._make_request("DELETE", f"/api/quizzes/{quiz_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete quiz: {e}")
            return False

    def get_quiz_job_status(self, job_id: str) -> Optional[Dict[Any, Any]]:
        """Get the status of a quiz generation job."""
        try:
            return api_client._make_request("GET", f"/api/quizzes/jobs/{job_id}")
        except Exception as e:
            logger.error(f"Failed to get quiz job status: {e}")
            return None

    # Quiz Template methods
    def get_quiz_templates(self) -> List[Dict[Any, Any]]:
        """Get all quiz templates."""
        try:
            result = api_client._make_request("GET", "/api/quizzes/templates")
            return result if isinstance(result, list) else [result]
        except Exception as e:
            logger.error(f"Failed to get quiz templates: {e}")
            return []

    def create_quiz_template(self, template_data: Dict) -> bool:
        """
        Create a new quiz template.
        
        Args:
            template_data: Dictionary containing template parameters
                - name: str (required)
                - description: str (required)
                - quiz_type: str (required)
                - default_question_count: int
                - difficulty_level: str
                - instructions: str (required)
                - content_requirements: Optional[str]
                - tags: List[str]
                - is_public: bool
        """
        try:
            # TODO: This endpoint needs to be implemented in the router
            # For now, we'll log and return False
            logger.warning("Create quiz template endpoint not yet implemented")
            return False
            # api_client._make_request("POST", "/api/quizzes/templates", json=template_data)
            # return True
        except Exception as e:
            logger.error(f"Failed to create quiz template: {e}")
            return False

    def update_quiz_template(self, template_id: str, template_data: Dict) -> bool:
        """Update a quiz template."""
        try:
            # TODO: This endpoint needs to be implemented in the router
            logger.warning("Update quiz template endpoint not yet implemented")
            return False
            # api_client._make_request("PUT", f"/api/quizzes/templates/{template_id}", json=template_data)
            # return True
        except Exception as e:
            logger.error(f"Failed to update quiz template: {e}")
            return False

    def delete_quiz_template(self, template_id: str) -> bool:
        """Delete a quiz template."""
        try:
            # TODO: This endpoint needs to be implemented in the router
            logger.warning("Delete quiz template endpoint not yet implemented")
            return False
            # api_client._make_request("DELETE", f"/api/quizzes/templates/{template_id}")
            # return True
        except Exception as e:
            logger.error(f"Failed to delete quiz template: {e}")
            return False

    def duplicate_quiz_template(self, template_id: str) -> bool:
        """Duplicate a quiz template."""
        try:
            # TODO: This endpoint needs to be implemented in the router
            logger.warning("Duplicate quiz template endpoint not yet implemented")
            return False
            # api_client._make_request("POST", f"/api/quizzes/templates/{template_id}/duplicate")
            # return True
        except Exception as e:
            logger.error(f"Failed to duplicate quiz template: {e}")
            return False

    # Quiz Profile methods
    def get_quiz_profiles(self) -> List[Dict[Any, Any]]:
        """Get all quiz profiles."""
        try:
            result = api_client._make_request("GET", "/api/quizzes/profiles")
            return result if isinstance(result, list) else [result]
        except Exception as e:
            logger.error(f"Failed to get quiz profiles: {e}")
            return []

    def create_quiz_profile(self, profile_data: Dict) -> bool:
        """
        Create a new quiz profile.
        
        Args:
            profile_data: Dictionary containing profile parameters
                - name: str (required)
                - description: Optional[str]
                - quiz_types: List[str]
                - difficulty_levels: List[str]
                - default_question_count: int
                - question_provider: str
                - question_model: str
                - evaluation_provider: Optional[str]
                - evaluation_model: Optional[str]
                - default_instructions: str
                - time_limit_minutes: Optional[int]
                - passing_score_percentage: int
        """
        try:
            # TODO: This endpoint needs to be implemented in the router
            logger.warning("Create quiz profile endpoint not yet implemented")
            return False
            # api_client._make_request("POST", "/api/quizzes/profiles", json=profile_data)
            # return True
        except Exception as e:
            logger.error(f"Failed to create quiz profile: {e}")
            return False

    def update_quiz_profile(self, profile_id: str, profile_data: Dict) -> bool:
        """Update a quiz profile."""
        try:
            # TODO: This endpoint needs to be implemented in the router
            logger.warning("Update quiz profile endpoint not yet implemented")
            return False
            # api_client._make_request("PUT", f"/api/quizzes/profiles/{profile_id}", json=profile_data)
            # return True
        except Exception as e:
            logger.error(f"Failed to update quiz profile: {e}")
            return False

    def delete_quiz_profile(self, profile_id: str) -> bool:
        """Delete a quiz profile."""
        try:
            # TODO: This endpoint needs to be implemented in the router
            logger.warning("Delete quiz profile endpoint not yet implemented")
            return False
            # api_client._make_request("DELETE", f"/api/quizzes/profiles/{profile_id}")
            # return True
        except Exception as e:
            logger.error(f"Failed to delete quiz profile: {e}")
            return False

    def duplicate_quiz_profile(self, profile_id: str) -> bool:
        """Duplicate a quiz profile."""
        try:
            # TODO: This endpoint needs to be implemented in the router
            logger.warning("Duplicate quiz profile endpoint not yet implemented")
            return False
            # api_client._make_request("POST", f"/api/quizzes/profiles/{profile_id}/duplicate")
            # return True
        except Exception as e:
            logger.error(f"Failed to duplicate quiz profile: {e}")
            return False

    # Utility methods for frontend
    def get_available_quiz_types(self) -> List[Dict[str, str]]:
        """Get available quiz types with labels and descriptions."""
        return [
            {"value": "multiple-choice", "label": "Multiple Choice", "description": "Questions with multiple answer options"},
            {"value": "true-false", "label": "True/False", "description": "Statements that must be identified as true or false"},
            {"value": "fill-blank", "label": "Fill in the Blank", "description": "Sentences with missing words or phrases to complete"},
            {"value": "problem-solving", "label": "Problem-Solving", "description": "Scenarios requiring application of knowledge to solve problems"},
            {"value": "mixed", "label": "Mixed Types", "description": "Combination of different question types"}
        ]

    def get_available_difficulty_levels(self) -> List[Dict[str, str]]:
        """Get available difficulty levels with descriptions."""
        return [
            {"value": "easy", "label": "Easy", "description": "Basic recall and understanding questions"},
            {"value": "medium", "label": "Medium", "description": "Application and analysis questions"},
            {"value": "hard", "label": "Hard", "description": "Evaluation and synthesis questions"}
        ]

    def validate_quiz_parameters(self, quiz_data: Dict) -> Dict[str, Any]:
        """
        Validate quiz generation parameters before submission.
        
        Returns:
            Dictionary with 'valid' boolean and 'errors' list
        """
        errors = []
        
        # Required fields
        if not quiz_data.get('quiz_profile'):
            errors.append("Quiz profile is required")
        
        if not quiz_data.get('quiz_title'):
            errors.append("Quiz title is required")
        
        if not quiz_data.get('content'):
            errors.append("Content is required")
        
        # Question count validation
        question_count = quiz_data.get('question_count', 10)
        if not isinstance(question_count, int) or question_count < 1 or question_count > 50:
            errors.append("Question count must be between 1 and 50")
        
        # Quiz type validation
        quiz_type = quiz_data.get('quiz_type', 'multiple-choice')
        valid_types = [t['value'] for t in self.get_available_quiz_types()]
        if quiz_type not in valid_types:
            errors.append(f"Invalid quiz type. Must be one of: {', '.join(valid_types)}")
        
        # Difficulty validation
        difficulty = quiz_data.get('difficulty', 'medium')
        valid_difficulties = [d['value'] for d in self.get_available_difficulty_levels()]
        if difficulty not in valid_difficulties:
            errors.append(f"Invalid difficulty. Must be one of: {', '.join(valid_difficulties)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


# Global service instance
quiz_api_service = QuizAPIService()