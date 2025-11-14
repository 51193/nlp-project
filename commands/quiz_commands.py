import time
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.quizzes import Quiz, QuizProfile, QuizTemplate
from open_notebook.plugins.quizzes import QuizGenerator, QuizGeneratorConfig


def full_model_dump(model):
    """Recursively dump model to dict, handling nested models"""
    if isinstance(model, BaseModel):
        return model.model_dump()
    elif isinstance(model, dict):
        return {k: full_model_dump(v) for k, v in model.items()}
    elif isinstance(model, list):
        return [full_model_dump(item) for item in model]
    else:
        return model


class QuizGenerationInput(CommandInput):
    """Input model for quiz generation command"""
    quiz_profile: str
    quiz_title: str
    content: str
    question_count: int = 10
    quiz_type: str = "multiple-choice"
    difficulty: str = "medium"
    quiz_template: Optional[str] = None
    notebook_id: Optional[str] = None
    source_ids: List[str] = []
    note_ids: List[str] = []


class QuizGenerationOutput(CommandOutput):
    """Output model for quiz generation command"""
    success: bool
    quiz_id: Optional[str] = None
    questions_generated: int = 0
    processing_time: float
    error_message: Optional[str] = None


@command("generate_quiz", app="open_notebook")
async def generate_quiz_command(
    input_data: QuizGenerationInput,
) -> QuizGenerationOutput:
    """
    Generate quiz questions based on content using the QuizGenerator plugin.
    Uses Quiz Profiles and Templates for configuration.
    """
    start_time = time.time()

    try:
        logger.info(f"Starting quiz generation for: {input_data.quiz_title}")
        logger.info(f"Using quiz profile: {input_data.quiz_profile}")
        logger.info(f"Quiz type: {input_data.quiz_type}, Difficulty: {input_data.difficulty}")

        # 1. Load Quiz Profile from database
        quiz_profile = await QuizProfile.get_by_name(input_data.quiz_profile)
        if not quiz_profile:
            raise ValueError(f"Quiz profile '{input_data.quiz_profile}' not found")

        # 2. Load Quiz Template if provided
        quiz_template = None
        if input_data.quiz_template:
            quiz_template = await QuizTemplate.get_by_name(input_data.quiz_template)
            if not quiz_template:
                logger.warning(f"Quiz template '{input_data.quiz_template}' not found, using default settings")

        # 3. Create QuizGenerator configuration
        # TODO: Load from database or use default configuration
        generator_config = QuizGeneratorConfig(
            name="default_quiz_generator",
            description="Default quiz generation configuration",
            question_provider=quiz_profile.question_provider,
            question_model=quiz_profile.question_model,
            evaluation_provider=quiz_profile.evaluation_provider,
            evaluation_model=quiz_profile.evaluation_model,
            default_question_count=quiz_profile.default_question_count,
        )

        # 4. Initialize QuizGenerator
        quiz_generator = QuizGenerator(generator_config)
        
        # 5. Generate quiz using the plugin
        quiz = await quiz_generator.generate_quiz(
            quiz_title=input_data.quiz_title,
            content=input_data.content,
            quiz_type=input_data.quiz_type,
            question_count=input_data.question_count,
            difficulty=input_data.difficulty,
            quiz_profile=quiz_profile,
            quiz_template=quiz_template,
        )

        # 6. Associate with command if available
        if input_data.execution_context:
            quiz.command = ensure_record_id(input_data.execution_context.command_id)
            await quiz.save()

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully generated quiz: {quiz.id} with {len(quiz.questions)} questions "
            f"in {processing_time:.2f}s"
        )

        return QuizGenerationOutput(
            success=True,
            quiz_id=str(quiz.id),
            questions_generated=len(quiz.questions),
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Quiz generation failed: {e}")
        logger.exception(e)

        return QuizGenerationOutput(
            success=False,
            processing_time=processing_time,
            error_message=str(e),
        )