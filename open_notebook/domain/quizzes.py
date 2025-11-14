from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel


class QuizProfile(ObjectModel):
    """
    Quiz Profile - Configuration for quiz generation.
    Defines the parameters and constraints for generating quizzes.
    """

    table_name: ClassVar[str] = "quiz_profile"

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    quiz_types: List[str] = Field(
        default=["multiple-choice"],
        description="Allowed quiz types: multiple-choice, true-false, fill-blank, problem-solving, mixed"
    )
    difficulty_levels: List[str] = Field(
        default=["easy", "medium", "hard"],
        description="Allowed difficulty levels"
    )
    default_question_count: int = Field(
        default=10,
        description="Default number of questions per quiz"
    )
    question_provider: str = Field(
        default=None,
        description="AI provider for question generation"
    )
    question_model: str = Field(
        default=None,
        description="AI model for question generation"
    )
    evaluation_provider: Optional[str] = Field(
        default=None,
        description="AI provider for answer evaluation"
    )
    evaluation_model: Optional[str] = Field(
        default=None,
        description="AI model for answer evaluation"
    )
    default_instructions: str = Field(
        default="Generate educational quiz questions based on the provided content.",
        description="Default instructions for quiz generation"
    )
    time_limit_minutes: Optional[int] = Field(
        default=None,
        description="Optional time limit for quiz completion"
    )
    passing_score_percentage: int = Field(
        default=60,
        description="Minimum score required to pass the quiz"
    )

    @field_validator("default_question_count")
    @classmethod
    def validate_question_count(cls, v):
        if not 1 <= v <= 50:
            raise ValueError("Question count must be between 1 and 50")
        return v

    @field_validator("passing_score_percentage")
    @classmethod
    def validate_passing_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Passing score must be between 0 and 100")
        return v

    @field_validator("quiz_types")
    @classmethod
    def validate_quiz_types(cls, v):
        valid_types = {"multiple-choice", "true-false", "fill-blank", "problem-solving", "mixed"}
        for quiz_type in v:
            if quiz_type not in valid_types:
                raise ValueError(f"Invalid quiz type: {quiz_type}. Must be one of {valid_types}")
        return v

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["QuizProfile"]:
        """Get quiz profile by name"""
        result = await repo_query(
            "SELECT * FROM quiz_profile WHERE name = $name", {"name": name}
        )
        if result:
            return cls(**result[0])
        return None


class QuizTemplate(ObjectModel):
    """
    Quiz Template - Predefined quiz configurations for reuse.
    Templates define the structure and parameters for quiz generation.
    """

    table_name: ClassVar[str] = "quiz_template"

    name: str = Field(..., description="Unique template name")
    description: str = Field(..., description="Template description")
    quiz_type: str = Field(
        ...,
        description="Type of quiz: multiple-choice, true-false, fill-blank, problem-solving, mixed"
    )
    default_question_count: int = Field(
        default=10,
        description="Default number of questions"
    )
    difficulty_level: str = Field(
        default="medium",
        description="Difficulty level: easy, medium, hard"
    )
    instructions: str = Field(
        ...,
        description="Specific instructions for quiz generation"
    )
    content_requirements: Optional[str] = Field(
        default=None,
        description="Requirements for source content to use with this template"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing templates"
    )
    is_public: bool = Field(
        default=False,
        description="Whether this template is publicly available"
    )

    @field_validator("quiz_type")
    @classmethod
    def validate_quiz_type(cls, v):
        valid_types = {"multiple-choice", "true-false", "fill-blank", "problem-solving", "mixed"}
        if v not in valid_types:
            raise ValueError(f"Invalid quiz type: {v}. Must be one of {valid_types}")
        return v

    @field_validator("difficulty_level")
    @classmethod
    def validate_difficulty(cls, v):
        valid_levels = {"easy", "medium", "hard"}
        if v not in valid_levels:
            raise ValueError(f"Invalid difficulty level: {v}. Must be one of {valid_levels}")
        return v

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["QuizTemplate"]:
        """Get quiz template by name"""
        result = await repo_query(
            "SELECT * FROM quiz_template WHERE name = $name", {"name": name}
        )
        if result:
            return cls(**result[0])
        return None

    @classmethod
    async def find_public_templates(cls) -> List["QuizTemplate"]:
        """Find all public quiz templates"""
        result = await repo_query(
            "SELECT * FROM quiz_template WHERE is_public = true"
        )
        return [cls(**item) for item in result]


class Quiz(ObjectModel):
    """
    Quiz - Represents a generated quiz with questions and answers.
    Tracks quiz state, results, and generation metadata.
    """

    table_name: ClassVar[str] = "quiz"

    title: str = Field(..., description="Quiz title")
    quiz_type: str = Field(
        ...,
        description="Type of quiz: multiple-choice, true-false, fill-blank, problem-solving, mixed"
    )
    question_count: int = Field(..., description="Number of questions in the quiz")
    status: str = Field(
        default="pending",
        description="Quiz status: pending, running, completed, failed, submitted"
    )
    quiz_profile: Dict[str, Any] = Field(
        ...,
        description="Quiz profile used for generation (stored as object)"
    )
    source_ids: List[str] = Field(
        default_factory=list,
        description="IDs of sources used for quiz content"
    )
    notebook_id: Optional[str] = Field(
        default=None,
        description="ID of the notebook this quiz belongs to"
    )
    note_ids: List[str] = Field(
        default_factory=list,
        description="IDs of specific notes used for quiz content"
    )
    questions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Generated quiz questions with answers"
    )
    user_answers: Dict[str, Any] = Field(
        default_factory=dict,
        description="User's answers to quiz questions"
    )
    score: Optional[float] = Field(
        default=None,
        description="User's score on the quiz (percentage)"
    )
    time_spent_seconds: Optional[int] = Field(
        default=None,
        description="Time spent completing the quiz in seconds"
    )
    command: Optional[Union[str, RecordID]] = Field(
        default=None,
        description="Link to surreal-commands generation job"
    )
    generated_at: Optional[str] = Field(
        default=None,
        description="Timestamp when quiz was generated"
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Timestamp when quiz was completed"
    )

    class Config:
        arbitrary_types_allowed = True

    async def get_job_status(self) -> Optional[str]:
        """Get the status of the associated generation command"""
        if not self.command:
            return None

        try:
            from surreal_commands import get_command_status

            status = await get_command_status(str(self.command))
            return status.status if status else "unknown"
        except Exception:
            return "unknown"

    @field_validator("command", mode="before")
    @classmethod
    def parse_command(cls, value):
        if isinstance(value, str):
            return ensure_record_id(value)
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = {"pending", "running", "completed", "failed", "submitted", "unknown"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
        return v

    def _prepare_save_data(self) -> dict:
        """Override to ensure command field is always RecordID format for database"""
        data = super()._prepare_save_data()
        
        # Ensure command field is RecordID format if not None
        if data.get("command") is not None:
            data["command"] = ensure_record_id(data["command"])
            
        return data

    async def calculate_score(self) -> float:
        """Calculate user's score based on submitted answers"""
        if not self.user_answers or not self.questions:
            return 0.0
        
        correct_count = 0
        total_questions = len(self.questions)
        
        for question in self.questions:
            question_id = question.get("id")
            if question_id in self.user_answers:
                user_answer = self.user_answers[question_id]
                correct_answer = question.get("correct_answer")
                
                if user_answer == correct_answer:
                    correct_count += 1
        
        return (correct_count / total_questions) * 100 if total_questions > 0 else 0.0

    async def submit_answers(self, answers: Dict[str, Any], time_spent: Optional[int] = None) -> float:
        """Submit user answers and calculate score"""
        self.user_answers = answers
        if time_spent is not None:
            self.time_spent_seconds = time_spent
        
        self.score = await self.calculate_score()
        self.status = "submitted"
        self.completed_at = self._get_current_timestamp()
        
        await self.save()
        return self.score

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


class QuizQuestion(ObjectModel):
    """
    Quiz Question - Individual question within a quiz.
    Supports multiple question types and formats.
    """

    table_name: ClassVar[str] = "quiz_question"

    quiz_id: str = Field(..., description="ID of the parent quiz")
    type: str = Field(
        ...,
        description="Question type: multiple-choice, true-false, fill-blank, problem-solving"
    )
    question: str = Field(..., description="The question text")
    options: Optional[List[str]] = Field(
        default=None,
        description="Available options for multiple-choice questions"
    )
    correct_answer: str = Field(..., description="The correct answer")
    explanation: Optional[str] = Field(
        default=None,
        description="Explanation of the correct answer"
    )
    difficulty: str = Field(
        default="medium",
        description="Question difficulty: easy, medium, hard"
    )
    points: int = Field(
        default=1,
        description="Points awarded for correct answer"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional question metadata"
    )
    order_index: int = Field(
        default=0,
        description="Order of question within the quiz"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        valid_types = {"multiple-choice", "true-false", "fill-blank", "problem-solving"}
        if v not in valid_types:
            raise ValueError(f"Invalid question type: {v}. Must be one of {valid_types}")
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v):
        valid_levels = {"easy", "medium", "hard"}
        if v not in valid_levels:
            raise ValueError(f"Invalid difficulty: {v}. Must be one of {valid_levels}")
        return v

    @classmethod
    async def find_by_quiz_id(cls, quiz_id: str) -> List["QuizQuestion"]:
        """Find all questions for a specific quiz"""
        result = await repo_query(
            "SELECT * FROM quiz_question WHERE quiz_id = $quiz_id ORDER BY order_index",
            {"quiz_id": quiz_id}
        )
        return [cls(**item) for item in result]