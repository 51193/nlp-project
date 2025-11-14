from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from api.quiz_service import (
    QuizGenerationRequest,
    QuizGenerationResponse,
    QuizSubmissionRequest,
    QuizSubmissionResponse,
    QuizService,
)

router = APIRouter()


class QuizResponse(BaseModel):
    """Response model for quiz data"""
    id: str
    title: str
    quiz_type: str
    question_count: int
    status: str
    quiz_profile: dict
    source_ids: List[str] = []
    notebook_id: Optional[str] = None
    note_ids: List[str] = []
    questions: List[dict] = []
    user_answers: Optional[dict] = None
    score: Optional[float] = None
    time_spent_seconds: Optional[int] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    job_status: Optional[str] = None


@router.get("/quizzes/templates")
async def list_quiz_templates():
    """List all available quiz templates"""
    try:
        templates = await QuizService.list_templates()
        return templates

    except Exception as e:
        logger.error(f"Error listing quiz templates: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list quiz templates: {str(e)}"
        )


@router.get("/quizzes/profiles")
async def list_quiz_profiles():
    """List all available quiz profiles"""
    try:
        profiles = await QuizService.list_profiles()
        return profiles

    except Exception as e:
        logger.error(f"Error listing quiz profiles: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list quiz profiles: {str(e)}"
        )


@router.post("/quizzes/generate", response_model=QuizGenerationResponse)
async def generate_quiz(request: QuizGenerationRequest):
    """
    Generate a quiz using Quiz Profiles and Templates.
    Returns immediately with job ID for status tracking.
    """
    try:
        job_id = await QuizService.submit_generation_job(
            quiz_profile_name=request.quiz_profile,
            quiz_template_name=request.quiz_template,
            quiz_title=request.quiz_title,
            notebook_id=request.notebook_id,
            source_ids=request.source_ids,
            note_ids=request.note_ids,
            content=request.content,
            question_count=request.question_count,
            quiz_type=request.quiz_type,
            difficulty=request.difficulty,
        )

        return QuizGenerationResponse(
            job_id=job_id,
            status="submitted",
            message=f"Quiz generation started for '{request.quiz_title}'",
            quiz_title=request.quiz_title,
            quiz_profile=request.quiz_profile,
        )

    except Exception as e:
        logger.error(f"Error generating quiz: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate quiz: {str(e)}"
        )


@router.get("/quizzes/jobs/{job_id}")
async def get_quiz_job_status(job_id: str):
    """Get the status of a quiz generation job"""
    try:
        status_data = await QuizService.get_job_status(job_id)
        return status_data

    except Exception as e:
        logger.error(f"Error fetching quiz job status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch job status: {str(e)}"
        )


@router.get("/quizzes", response_model=List[QuizResponse])
async def list_quizzes():
    """List all quizzes"""
    try:
        quizzes = await QuizService.list_quizzes()

        response_quizzes = []
        for quiz in quizzes:
            job_status = None
            if quiz.command:
                try:
                    job_status = await quiz.get_job_status()
                except Exception:
                    job_status = "unknown"
            else:
                job_status = "completed"

            response_quizzes.append(
                QuizResponse(
                    id=str(quiz.id),
                    title=quiz.title,
                    quiz_type=quiz.quiz_type,
                    question_count=quiz.question_count,
                    status=quiz.status,
                    quiz_profile=quiz.quiz_profile,
                    source_ids=quiz.source_ids,
                    notebook_id=quiz.notebook_id,
                    note_ids=quiz.note_ids,
                    questions=quiz.questions,
                    user_answers=quiz.user_answers,
                    score=quiz.score,
                    time_spent_seconds=quiz.time_spent_seconds,
                    created=str(quiz.created) if quiz.created else None,
                    updated=str(quiz.updated) if quiz.updated else None,
                    job_status=job_status,
                )
            )

        return response_quizzes

    except Exception as e:
        logger.error(f"Error listing quizzes: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list quizzes: {str(e)}"
        )


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(quiz_id: str):
    """Get a specific quiz"""
    try:
        quiz = await QuizService.get_quiz(quiz_id)

        job_status = None
        if quiz.command:
            try:
                job_status = await quiz.get_job_status()
            except Exception:
                job_status = "unknown"
        else:
            job_status = "completed"

        return QuizResponse(
            id=str(quiz.id),
            title=quiz.title,
            quiz_type=quiz.quiz_type,
            question_count=quiz.question_count,
            status=quiz.status,
            quiz_profile=quiz.quiz_profile,
            source_ids=quiz.source_ids,
            notebook_id=quiz.notebook_id,
            note_ids=quiz.note_ids,
            questions=quiz.questions,
            user_answers=quiz.user_answers,
            score=quiz.score,
            time_spent_seconds=quiz.time_spent_seconds,
            created=str(quiz.created) if quiz.created else None,
            updated=str(quiz.updated) if quiz.updated else None,
            job_status=job_status,
        )

    except Exception as e:
        logger.error(f"Error fetching quiz: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Quiz not found: {str(e)}")


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizSubmissionResponse)
async def submit_quiz_answers(quiz_id: str, request: QuizSubmissionRequest):
    """Submit answers for a quiz and calculate score"""
    try:
        result = await QuizService.submit_quiz_answers(
            quiz_id=quiz_id,
            answers=request.answers,
            time_spent_seconds=request.time_spent_seconds
        )

        return QuizSubmissionResponse(
            quiz_id=quiz_id,
            score=result.score,
            total_questions=result.total_questions,
            correct_answers=result.correct_answers,
            passed=result.passed,
            time_spent_seconds=result.time_spent_seconds,
        )

    except Exception as e:
        logger.error(f"Error submitting quiz answers: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to submit quiz answers: {str(e)}"
        )


@router.delete("/quizzes/{quiz_id}")
async def delete_quiz(quiz_id: str):
    """Delete a quiz"""
    try:
        await QuizService.delete_quiz(quiz_id)

        logger.info(f"Deleted quiz: {quiz_id}")
        return {"message": "Quiz deleted successfully", "quiz_id": quiz_id}

    except Exception as e:
        logger.error(f"Error deleting quiz: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete quiz: {str(e)}")


# @router.get("/quizzes/templates")
# async def list_quiz_templates():
#     """List all available quiz templates"""
#     try:
#         templates = await QuizService.list_templates()
#         return templates

#     except Exception as e:
#         logger.error(f"Error listing quiz templates: {str(e)}")
#         raise HTTPException(
#             status_code=500, detail=f"Failed to list quiz templates: {str(e)}"
#         )


# @router.get("/quizzes/profiles")
# async def list_quiz_profiles():
#     """List all available quiz profiles"""
#     try:
#         profiles = await QuizService.list_profiles()
#         return profiles

#     except Exception as e:
#         logger.error(f"Error listing quiz profiles: {str(e)}")
#         raise HTTPException(
#             status_code=500, detail=f"Failed to list quiz profiles: {str(e)}"
#         )


from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

# Add new request/response models for template and profile CRUD operations
class QuizTemplateCreateRequest(BaseModel):
    """Request model for creating a quiz template"""
    name: str
    description: str
    quiz_type: str
    default_question_count: int = 10
    difficulty_level: str = "medium"
    instructions: str
    content_requirements: Optional[str] = None
    tags: List[str] = []
    is_public: bool = False


class QuizTemplateUpdateRequest(BaseModel):
    """Request model for updating a quiz template"""
    name: Optional[str] = None
    description: Optional[str] = None
    quiz_type: Optional[str] = None
    default_question_count: Optional[int] = None
    difficulty_level: Optional[str] = None
    instructions: Optional[str] = None
    content_requirements: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class QuizTemplateResponse(BaseModel):
    """Response model for quiz template data"""
    id: str
    name: str
    description: str
    quiz_type: str
    default_question_count: int
    difficulty_level: str
    instructions: str
    content_requirements: Optional[str] = None
    tags: List[str] = []
    is_public: bool
    created: Optional[str] = None
    updated: Optional[str] = None


class QuizProfileCreateRequest(BaseModel):
    """Request model for creating a quiz profile"""
    name: str
    description: Optional[str] = None
    quiz_types: List[str] = ["multiple-choice"]
    difficulty_levels: List[str] = ["easy", "medium", "hard"]
    default_question_count: int = 10
    question_provider: str = "openai"
    question_model: str = "gpt-4"
    evaluation_provider: Optional[str] = None
    evaluation_model: Optional[str] = None
    default_instructions: str = "Generate educational quiz questions based on the provided content."
    time_limit_minutes: Optional[int] = None
    passing_score_percentage: int = 70


class QuizProfileUpdateRequest(BaseModel):
    """Request model for updating a quiz profile"""
    name: Optional[str] = None
    description: Optional[str] = None
    quiz_types: Optional[List[str]] = None
    difficulty_levels: Optional[List[str]] = None
    default_question_count: Optional[int] = None
    question_provider: Optional[str] = None
    question_model: Optional[str] = None
    evaluation_provider: Optional[str] = None
    evaluation_model: Optional[str] = None
    default_instructions: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    passing_score_percentage: Optional[int] = None


class QuizProfileResponse(BaseModel):
    """Response model for quiz profile data"""
    id: str
    name: str
    description: Optional[str] = None
    quiz_types: List[str] = []
    difficulty_levels: List[str] = []
    default_question_count: int
    question_provider: str
    question_model: str
    evaluation_provider: Optional[str] = None
    evaluation_model: Optional[str] = None
    default_instructions: str
    time_limit_minutes: Optional[int] = None
    passing_score_percentage: int
    created: Optional[str] = None
    updated: Optional[str] = None


# Add these CRUD endpoints to the existing router

@router.post("/quizzes/templates", response_model=QuizTemplateResponse)
async def create_quiz_template(request: QuizTemplateCreateRequest):
    """Create a new quiz template"""
    try:
        logger.info(f"Creating quiz template: {request.name}")
        
        # Create template using domain model
        from open_notebook.domain.quizzes import QuizTemplate
        
        template_data = request.model_dump()
        quiz_template = QuizTemplate(**template_data)
        await quiz_template.save()
        
        logger.info(f"Successfully created quiz template: {quiz_template.id}")
        
        return QuizTemplateResponse(
            id=str(quiz_template.id),
            name=quiz_template.name,
            description=quiz_template.description,
            quiz_type=quiz_template.quiz_type,
            default_question_count=quiz_template.default_question_count,
            difficulty_level=quiz_template.difficulty_level,
            instructions=quiz_template.instructions,
            content_requirements=quiz_template.content_requirements,
            tags=quiz_template.tags,
            is_public=quiz_template.is_public,
            created=str(quiz_template.created) if quiz_template.created else None,
            updated=str(quiz_template.updated) if quiz_template.updated else None,
        )
        
    except Exception as e:
        logger.error(f"Error creating quiz template: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create quiz template: {str(e)}"
        )


@router.put("/quizzes/templates/{template_id}", response_model=QuizTemplateResponse)
async def update_quiz_template(template_id: str, request: QuizTemplateUpdateRequest):
    """Update a quiz template"""
    try:
        logger.info(f"Updating quiz template: {template_id}")
        
        # Get existing template
        from open_notebook.domain.quizzes import QuizTemplate
        quiz_template = await QuizTemplate.get(template_id)
        if not quiz_template:
            raise HTTPException(status_code=404, detail="Quiz template not found")
        
        # Update fields from request
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(quiz_template, field):
                setattr(quiz_template, field, value)
        
        await quiz_template.save()
        
        logger.info(f"Successfully updated quiz template: {quiz_template.id}")
        
        return QuizTemplateResponse(
            id=str(quiz_template.id),
            name=quiz_template.name,
            description=quiz_template.description,
            quiz_type=quiz_template.quiz_type,
            default_question_count=quiz_template.default_question_count,
            difficulty_level=quiz_template.difficulty_level,
            instructions=quiz_template.instructions,
            content_requirements=quiz_template.content_requirements,
            tags=quiz_template.tags,
            is_public=quiz_template.is_public,
            created=str(quiz_template.created) if quiz_template.created else None,
            updated=str(quiz_template.updated) if quiz_template.updated else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating quiz template: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update quiz template: {str(e)}"
        )


@router.delete("/quizzes/templates/{template_id}")
async def delete_quiz_template(template_id: str):
    """Delete a quiz template"""
    try:
        logger.info(f"Deleting quiz template: {template_id}")
        
        # Get template to ensure it exists
        from open_notebook.domain.quizzes import QuizTemplate
        quiz_template = await QuizTemplate.get(template_id)
        if not quiz_template:
            raise HTTPException(status_code=404, detail="Quiz template not found")
        
        # Delete the template
        await quiz_template.delete()
        
        logger.info(f"Successfully deleted quiz template: {template_id}")
        return {"message": "Quiz template deleted successfully", "template_id": template_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quiz template: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete quiz template: {str(e)}"
        )


@router.post("/quizzes/templates/{template_id}/duplicate", response_model=QuizTemplateResponse)
async def duplicate_quiz_template(template_id: str):
    """Duplicate a quiz template"""
    try:
        logger.info(f"Duplicating quiz template: {template_id}")
        
        # Get existing template
        from open_notebook.domain.quizzes import QuizTemplate
        original_template = await QuizTemplate.get(template_id)
        if not original_template:
            raise HTTPException(status_code=404, detail="Quiz template not found")
        
        # Create a copy with a new name
        import copy
        template_data = original_template.model_dump()
        template_data['name'] = f"{original_template.name} (Copy)"
        template_data.pop('id', None)  # Remove ID to create new record
        
        new_template = QuizTemplate(**template_data)
        await new_template.save()
        
        logger.info(f"Successfully duplicated quiz template: {new_template.id}")
        
        return QuizTemplateResponse(
            id=str(new_template.id),
            name=new_template.name,
            description=new_template.description,
            quiz_type=new_template.quiz_type,
            default_question_count=new_template.default_question_count,
            difficulty_level=new_template.difficulty_level,
            instructions=new_template.instructions,
            content_requirements=new_template.content_requirements,
            tags=new_template.tags,
            is_public=new_template.is_public,
            created=str(new_template.created) if new_template.created else None,
            updated=str(new_template.updated) if new_template.updated else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating quiz template: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to duplicate quiz template: {str(e)}"
        )


@router.post("/quizzes/profiles", response_model=QuizProfileResponse)
async def create_quiz_profile(request: QuizProfileCreateRequest):
    """Create a new quiz profile"""
    try:
        logger.info(f"Creating quiz profile: {request.name}")
        
        # Create profile using domain model
        from open_notebook.domain.quizzes import QuizProfile
        
        profile_data = request.model_dump()
        quiz_profile = QuizProfile(**profile_data)
        await quiz_profile.save()
        
        logger.info(f"Successfully created quiz profile: {quiz_profile.id}")
        
        return QuizProfileResponse(
            id=str(quiz_profile.id),
            name=quiz_profile.name,
            description=quiz_profile.description,
            quiz_types=quiz_profile.quiz_types,
            difficulty_levels=quiz_profile.difficulty_levels,
            default_question_count=quiz_profile.default_question_count,
            question_provider=quiz_profile.question_provider,
            question_model=quiz_profile.question_model,
            evaluation_provider=quiz_profile.evaluation_provider,
            evaluation_model=quiz_profile.evaluation_model,
            default_instructions=quiz_profile.default_instructions,
            time_limit_minutes=quiz_profile.time_limit_minutes,
            passing_score_percentage=quiz_profile.passing_score_percentage,
            created=str(quiz_profile.created) if quiz_profile.created else None,
            updated=str(quiz_profile.updated) if quiz_profile.updated else None,
        )
        
    except Exception as e:
        logger.error(f"Error creating quiz profile: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create quiz profile: {str(e)}"
        )


@router.put("/quizzes/profiles/{profile_id}", response_model=QuizProfileResponse)
async def update_quiz_profile(profile_id: str, request: QuizProfileUpdateRequest):
    """Update a quiz profile"""
    try:
        logger.info(f"Updating quiz profile: {profile_id}")
        
        # Get existing profile
        from open_notebook.domain.quizzes import QuizProfile
        quiz_profile = await QuizProfile.get(profile_id)
        if not quiz_profile:
            raise HTTPException(status_code=404, detail="Quiz profile not found")
        
        # Update fields from request
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(quiz_profile, field):
                setattr(quiz_profile, field, value)
        
        await quiz_profile.save()
        
        logger.info(f"Successfully updated quiz profile: {quiz_profile.id}")
        
        return QuizProfileResponse(
            id=str(quiz_profile.id),
            name=quiz_profile.name,
            description=quiz_profile.description,
            quiz_types=quiz_profile.quiz_types,
            difficulty_levels=quiz_profile.difficulty_levels,
            default_question_count=quiz_profile.default_question_count,
            question_provider=quiz_profile.question_provider,
            question_model=quiz_profile.question_model,
            evaluation_provider=quiz_profile.evaluation_provider,
            evaluation_model=quiz_profile.evaluation_model,
            default_instructions=quiz_profile.default_instructions,
            time_limit_minutes=quiz_profile.time_limit_minutes,
            passing_score_percentage=quiz_profile.passing_score_percentage,
            created=str(quiz_profile.created) if quiz_profile.created else None,
            updated=str(quiz_profile.updated) if quiz_profile.updated else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating quiz profile: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update quiz profile: {str(e)}"
        )


@router.delete("/quizzes/profiles/{profile_id}")
async def delete_quiz_profile(profile_id: str):
    """Delete a quiz profile"""
    try:
        logger.info(f"Deleting quiz profile: {profile_id}")
        
        # Get profile to ensure it exists
        from open_notebook.domain.quizzes import QuizProfile
        quiz_profile = await QuizProfile.get(profile_id)
        if not quiz_profile:
            raise HTTPException(status_code=404, detail="Quiz profile not found")
        
        # Delete the profile
        await quiz_profile.delete()
        
        logger.info(f"Successfully deleted quiz profile: {profile_id}")
        return {"message": "Quiz profile deleted successfully", "profile_id": profile_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting quiz profile: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete quiz profile: {str(e)}"
        )


@router.post("/quizzes/profiles/{profile_id}/duplicate", response_model=QuizProfileResponse)
async def duplicate_quiz_profile(profile_id: str):
    """Duplicate a quiz profile"""
    try:
        logger.info(f"Duplicating quiz profile: {profile_id}")
        
        # Get existing profile
        from open_notebook.domain.quizzes import QuizProfile
        original_profile = await QuizProfile.get(profile_id)
        if not original_profile:
            raise HTTPException(status_code=404, detail="Quiz profile not found")
        
        # Create a copy with a new name
        profile_data = original_profile.model_dump()
        profile_data['name'] = f"{original_profile.name} (Copy)"
        profile_data.pop('id', None)  # Remove ID to create new record
        
        new_profile = QuizProfile(**profile_data)
        await new_profile.save()
        
        logger.info(f"Successfully duplicated quiz profile: {new_profile.id}")
        
        return QuizProfileResponse(
            id=str(new_profile.id),
            name=new_profile.name,
            description=new_profile.description,
            quiz_types=new_profile.quiz_types,
            difficulty_levels=new_profile.difficulty_levels,
            default_question_count=new_profile.default_question_count,
            question_provider=new_profile.question_provider,
            question_model=new_profile.question_model,
            evaluation_provider=new_profile.evaluation_provider,
            evaluation_model=new_profile.evaluation_model,
            default_instructions=new_profile.default_instructions,
            time_limit_minutes=new_profile.time_limit_minutes,
            passing_score_percentage=new_profile.passing_score_percentage,
            created=str(new_profile.created) if new_profile.created else None,
            updated=str(new_profile.updated) if new_profile.updated else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating quiz profile: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to duplicate quiz profile: {str(e)}"
        )