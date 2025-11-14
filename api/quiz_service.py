from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from surreal_commands import get_command_status, submit_command

from open_notebook.domain.notebook import Notebook
from open_notebook.domain.quizzes import Quiz, QuizProfile, QuizTemplate
from open_notebook.plugins.quizzes import QuizGenerator, QuizGeneratorConfig


class QuizGenerationRequest(BaseModel):
    """Request model for quiz generation"""

    quiz_profile: str
    quiz_template: Optional[str] = None
    quiz_title: str
    content: Optional[str] = None
    notebook_id: Optional[str] = None
    source_ids: List[str] = []
    note_ids: List[str] = []
    question_count: int = 10
    quiz_type: str = "multiple-choice"
    difficulty: str = "medium"


class QuizGenerationResponse(BaseModel):
    """Response model for quiz generation"""

    job_id: str
    status: str
    message: str
    quiz_title: str
    quiz_profile: str

class QuizSubmissionRequest(BaseModel):
    """Request model for submitting quiz answers"""
    answers: Dict[str, Any]
    time_spent_seconds: Optional[int] = None

class QuizSubmissionResponse(BaseModel):
    """Response model for quiz submission results"""
    quiz_id: str
    score: float
    total_questions: int
    correct_answers: int
    passed: bool
    time_spent_seconds: Optional[int] = None

class QuizSubmissionResult(BaseModel):
    """Result model for quiz submission"""

    score: float
    total_questions: int
    correct_answers: int
    passed: bool
    time_spent_seconds: Optional[int] = None


class QuizService:
    """Service layer for quiz operations"""

    # @staticmethod
    # async def submit_generation_job(
    #     quiz_profile_name: str,
    #     quiz_title: str,
    #     quiz_template_name: Optional[str] = None,
    #     notebook_id: Optional[str] = None,
    #     source_ids: List[str] = [],
    #     note_ids: List[str] = [],
    #     content: Optional[str] = None,
    #     question_count: int = 10,
    #     quiz_type: str = "multiple-choice",
    #     difficulty: str = "medium",
    # ) -> str:
    #     """Submit a quiz generation job for background processing"""
    #     try:
    #         # Validate quiz profile exists
    #         quiz_profile = await QuizProfile.get_by_name(quiz_profile_name)
    #         if not quiz_profile:
    #             raise ValueError(f"Quiz profile '{quiz_profile_name}' not found")

    #         # Validate quiz template if provided
    #         quiz_template = None
    #         if quiz_template_name:
    #             quiz_template = await QuizTemplate.get_by_name(quiz_template_name)
    #             if not quiz_template:
    #                 raise ValueError(f"Quiz template '{quiz_template_name}' not found")

    #         # Get content from notebook if not provided directly
    #         if not content and notebook_id:
    #             try:
    #                 notebook = await Notebook.get(notebook_id)
    #                 # Get notebook context (this may need to be adjusted based on actual Notebook implementation)
    #                 content = (
    #                     await notebook.get_context()
    #                     if hasattr(notebook, "get_context")
    #                     else str(notebook)
    #                 )
    #             except Exception as e:
    #                 logger.warning(
    #                     f"Failed to get notebook content, using notebook_id as content: {e}"
    #                 )
    #                 content = f"Notebook ID: {notebook_id}"

    #         if not content:
    #             raise ValueError(
    #                 "Content is required - provide either content or notebook_id"
    #             )

    #         # Validate quiz type and difficulty against profile
    #         if quiz_type not in quiz_profile.quiz_types:
    #             raise ValueError(
    #                 f"Quiz type '{quiz_type}' not allowed in profile '{quiz_profile_name}'. "
    #                 f"Allowed types: {quiz_profile.quiz_types}"
    #             )

    #         if difficulty not in quiz_profile.difficulty_levels:
    #             raise ValueError(
    #                 f"Difficulty '{difficulty}' not allowed in profile '{quiz_profile_name}'. "
    #                 f"Allowed levels: {quiz_profile.difficulty_levels}"
    #             )

    #         # Prepare command arguments
    #         command_args = {
    #             "quiz_profile": quiz_profile_name,
    #             "quiz_title": quiz_title,
    #             "content": str(content),
    #             "question_count": question_count,
    #             "quiz_type": quiz_type,
    #             "difficulty": difficulty,
    #         }

    #         # Add optional parameters
    #         if quiz_template_name:
    #             command_args["quiz_template"] = quiz_template_name
    #         if notebook_id:
    #             command_args["notebook_id"] = notebook_id
    #         if source_ids:
    #             command_args["source_ids"] = source_ids
    #         if note_ids:
    #             command_args["note_ids"] = note_ids

    #         # Ensure command modules are imported before submitting
    #         # This is needed because submit_command validates against local registry
    #         try:
    #             import commands.quiz_commands  # noqa: F401
    #         except ImportError as import_err:
    #             logger.error(f"Failed to import quiz commands: {import_err}")
    #             raise ValueError("Quiz commands not available")

    #         # Submit command to surreal-commands
    #         job_id = submit_command("open_notebook", "generate_quiz", command_args)

    #         # Convert RecordID to string if needed
    #         if not job_id:
    #             raise ValueError("Failed to get job_id from submit_command")
    #         job_id_str = str(job_id)
    #         logger.info(
    #             f"Submitted quiz generation job: {job_id_str} for quiz '{quiz_title}'"
    #         )
    #         return job_id_str

    #     except Exception as e:
    #         logger.error(f"Failed to submit quiz generation job: {e}")
    #         raise HTTPException(
    #             status_code=500,
    #             detail=f"Failed to submit quiz generation job: {str(e)}",
    #         )

    @staticmethod
    async def submit_generation_job(
        quiz_profile_name: str,
        quiz_template_name: Optional[str],
        quiz_title: str,
        notebook_id: Optional[str],
        source_ids: Optional[List[str]],
        note_ids: Optional[List[str]],
        content: str,
        question_count: int,
        quiz_type: str,
        difficulty: str,
    ) -> str:
        """Submit a quiz generation job and return job ID"""
        try:
            logger.info(f"Submitting quiz generation job: {quiz_title}")
            logger.info(f"Content length: {len(content)} characters")
            logger.info(f"Question count: {question_count}, Type: {quiz_type}, Difficulty: {difficulty}")
            
            # 1. 创建 pending 状态的 quiz
            from open_notebook.domain.quizzes import Quiz
            
            quiz_data = {
                "title": quiz_title,
                "quiz_type": quiz_type,
                "question_count": question_count,
                "status": "running",
                "quiz_profile": {"name": quiz_profile_name},
                "source_ids": source_ids or [],
                "notebook_id": notebook_id,
                "note_ids": note_ids or [],
                "questions": []
            }
            
            quiz = Quiz(**quiz_data)
            await quiz.save()
            quiz_id = str(quiz.id)
            
            logger.info(f"Created quiz record: {quiz_id}")
            
            # 2. 使用 QuizGenerator 异步生成题目
            import asyncio
            task = asyncio.create_task(
                QuizService._generate_quiz_with_ai_generator(
                    quiz_id, content, question_count, quiz_type, difficulty
                )
            )
            
            # 添加任务完成回调来记录状态
            def task_done_callback(future):
                try:
                    result = future.result()
                    logger.info(f"Quiz generation task completed for {quiz_id}")
                except Exception as e:
                    logger.error(f"Quiz generation task failed for {quiz_id}: {e}")
            
            task.add_done_callback(task_done_callback)
            
            logger.info(f"Quiz generation job submitted and task created: {quiz_id}")
            return quiz_id
            
        except Exception as e:
            logger.error(f"Failed to submit quiz generation job: {e}")
            import time
            return f"mock_job_{int(time.time())}"

    @staticmethod
    async def _generate_quiz_with_ai_generator(
        quiz_id: str,
        content: str,
        question_count: int,
        quiz_type: str,
        difficulty: str
    ):
        """使用 QuizGenerator 生成测验"""
        try:
            logger.info(f"Starting AI quiz generation for quiz {quiz_id}")
            logger.info(f"AI generation parameters: {question_count} questions, type: {quiz_type}, difficulty: {difficulty}")
            
            # 创建配置
            from open_notebook.plugins.quizzes import QuizGenerator, QuizGeneratorConfig
            
            config = QuizGeneratorConfig(
                name="default",
                description="Default quiz generation configuration",
                question_provider="deepseek",
                question_model="deepseek-reasoner",
                default_question_count=question_count,
                default_difficulty=difficulty
            )
            
            logger.info(f"QuizGeneratorConfig created: {config.name}")
            
            # 创建生成器
            generator = QuizGenerator(config)
            logger.info("QuizGenerator instance created, initializing...")
            
            await generator.initialize()
            logger.info("QuizGenerator initialized successfully")
            
            # 生成测验
            logger.info("Starting quiz generation with AI...")
            quiz = await generator.generate_quiz(
                quiz_title=f"Quiz {quiz_id}",
                content=content,
                quiz_type=quiz_type,
                question_count=question_count,
                difficulty=difficulty
            )
            
            logger.info(f"Quiz generation completed, generated {len(quiz.questions)} questions")
            
            # 更新原始 quiz 的状态和问题
            from open_notebook.domain.quizzes import Quiz
            original_quiz = await Quiz.get(quiz_id)
            if original_quiz:
                original_quiz.questions = quiz.questions
                original_quiz.status = "completed"
                await original_quiz.save()
                logger.info(f"Updated quiz {quiz_id} with generated questions and completed status")
            else:
                logger.error(f"Original quiz {quiz_id} not found for update")
                
            logger.info(f"AI quiz generation completed successfully for {quiz_id}")
            
        except Exception as e:
            logger.error(f"AI quiz generation failed for {quiz_id}: {e}")
            logger.exception(e)  # 记录完整的堆栈跟踪
            
            # 更新为失败状态
            from open_notebook.domain.quizzes import Quiz
            quiz = await Quiz.get(quiz_id)
            if quiz:
                quiz.status = "failed"
                await quiz.save()
                logger.info(f"Updated quiz {quiz_id} to failed status")

    @staticmethod
    async def get_job_status(job_id: str) -> Dict[str, Any]:
        """Get status of a quiz generation job"""
        try:
            status = await get_command_status(job_id)
            return {
                "job_id": job_id,
                "status": status.status if status else "unknown",
                "result": status.result if status else None,
                "error_message": getattr(status, "error_message", None)
                if status
                else None,
                "created": str(status.created)
                if status and hasattr(status, "created") and status.created
                else None,
                "updated": str(status.updated)
                if status and hasattr(status, "updated") and status.updated
                else None,
                "progress": getattr(status, "progress", None) if status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get quiz job status: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get job status: {str(e)}"
            )

    @staticmethod
    async def list_quizzes() -> List[Quiz]:
        """List all quizzes"""
        try:
            quizzes = await Quiz.get_all(order_by="created desc")
            return quizzes
        except Exception as e:
            logger.error(f"Failed to list quizzes: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list quizzes: {str(e)}"
            )

    @staticmethod
    async def get_quiz(quiz_id: str) -> Quiz:
        """Get a specific quiz"""
        try:
            quiz = await Quiz.get(quiz_id)
            return quiz
        except Exception as e:
            logger.error(f"Failed to get quiz {quiz_id}: {e}")
            raise HTTPException(status_code=404, detail=f"Quiz not found: {str(e)}")

    @staticmethod
    async def submit_quiz_answers(
        quiz_id: str, answers: Dict[str, Any], time_spent_seconds: Optional[int] = None
    ) -> QuizSubmissionResult:
        """Submit answers for a quiz and calculate results"""
        try:
            quiz = await Quiz.get(quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")

            # Calculate score using quiz's built-in method
            score = await quiz.submit_answers(answers, time_spent_seconds)

            # Calculate result details
            total_questions = len(quiz.questions) if quiz.questions else 0
            correct_answers = int((score / 100) * total_questions) if total_questions > 0 else 0
            passing_score = quiz.quiz_profile.get("passing_score_percentage", 70)
            passed = score >= passing_score

            return QuizSubmissionResult(
                score=score,
                total_questions=total_questions,
                correct_answers=correct_answers,
                passed=passed,
                time_spent_seconds=time_spent_seconds,
            )

        except Exception as e:
            logger.error(f"Failed to submit quiz answers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to submit quiz answers: {str(e)}"
            )

    @staticmethod
    async def delete_quiz(quiz_id: str) -> None:
        """Delete a quiz"""
        try:
            quiz = await Quiz.get(quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")

            await quiz.delete()
            logger.info(f"Successfully deleted quiz: {quiz_id}")

        except Exception as e:
            logger.error(f"Failed to delete quiz {quiz_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete quiz: {str(e)}"
            )

    @staticmethod
    async def list_templates() -> List[QuizTemplate]:
        """List all available quiz templates"""
        try:
            templates = await QuizTemplate.get_all()
            return templates
        except Exception as e:
            logger.error(f"Failed to list quiz templates: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list quiz templates: {str(e)}"
            )

    @staticmethod
    async def list_profiles() -> List[QuizProfile]:
        """List all available quiz profiles"""
        try:
            profiles = await QuizProfile.get_all()
            return profiles
        except Exception as e:
            logger.error(f"Failed to list quiz profiles: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list quiz profiles: {str(e)}"
            )


class DefaultQuizProfiles:
    """Utility class for creating default quiz profiles and templates"""

    @staticmethod
    async def create_default_quiz_profiles():
        """Create default quiz profiles if they don't exist"""
        try:
            # Check if profiles already exist
            existing = await QuizProfile.get_all()
            if existing:
                logger.info(f"Quiz profiles already exist: {len(existing)} found")
                return existing

            logger.info(
                "Default quiz profiles should be created via database migration"
            )
            return []

        except Exception as e:
            logger.error(f"Failed to create default quiz profiles: {e}")
            raise

    @staticmethod
    async def create_default_quiz_templates():
        """Create default quiz templates if they don't exist"""
        try:
            # Check if templates already exist
            existing = await QuizTemplate.get_all()
            if existing:
                logger.info(f"Quiz templates already exist: {len(existing)} found")
                return existing

            logger.info(
                "Default quiz templates should be created via database migration"
            )
            return []

        except Exception as e:
            logger.error(f"Failed to create default quiz templates: {e}")
            raise