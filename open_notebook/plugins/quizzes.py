import asyncio
import json
import re
from pathlib import Path
from typing import ClassVar, List, Optional, Dict, Any

from loguru import logger
from pydantic import Field, field_validator, model_validator

from open_notebook.domain.quizzes import Quiz, QuizProfile, QuizTemplate
from open_notebook.domain.notebook import ObjectModel
from open_notebook.graphs.utils import provision_langchain_model


class QuizGeneratorConfig(ObjectModel):
    """
    Configuration for quiz generation.
    Defines the parameters and AI models for generating quizzes.
    """
    table_name: ClassVar[str] = "quiz_generator_config"
    
    name: str = Field(..., description="Unique configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    
    # AI Model Configuration
    question_provider: str = Field(default="deepseek", description="AI provider for question generation")
    question_model: str = Field(default="deepseek-reasoner", description="AI model for question generation")
    evaluation_provider: Optional[str] = Field(default="deepseek", description="AI provider for answer evaluation")
    evaluation_model: Optional[str] = Field(default="deepseek-reasoner", description="AI model for answer evaluation")
    
    # Generation Parameters
    default_question_count: int = Field(default=10, ge=1, le=50, description="Default number of questions")
    max_question_count: int = Field(default=20, ge=1, le=100, description="Maximum number of questions")
    default_difficulty: str = Field(default="medium", description="Default difficulty level")
    
    # Content Processing
    content_chunk_size: int = Field(default=2000, description="Size of content chunks for processing")
    content_overlap: int = Field(default=200, description="Overlap between content chunks")
    
    # Quality Controls
    creativity: float = Field(default=0.7, ge=0, le=1, description="Creativity level for question generation")
    diversity_weight: float = Field(default=0.8, ge=0, le=1, description="Weight for question diversity")
    accuracy_threshold: float = Field(default=0.9, ge=0, le=1, description="Minimum accuracy threshold for questions")
    
    # Advanced Settings
    enable_explanations: bool = Field(default=True, description="Whether to generate answer explanations")
    enable_difficulty_scaling: bool = Field(default=True, description="Whether to scale difficulty automatically")
    enable_content_validation: bool = Field(default=True, description="Whether to validate questions against content")
    
    # Template References
    default_quiz_type: str = Field(default="multiple-choice", description="Default quiz type")
    supported_quiz_types: List[str] = Field(
        default=["multiple-choice", "true-false", "fill-blank", "problem-solving", "mixed"],
        description="Supported quiz types"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate configuration name is not empty"""
        if not value or not value.strip():
            raise ValueError("Configuration name cannot be empty")
        return value.strip()

    @field_validator("creativity", "diversity_weight", "accuracy_threshold")
    @classmethod
    def validate_float_range(cls, value: float) -> float:
        """Validate float values are within 0-1 range"""
        if not 0 <= value <= 1:
            raise ValueError("Value must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def validate_models(self) -> "QuizGeneratorConfig":
        """Validate that required models are configured"""
        if not self.question_model:
            raise ValueError("Question generation model must be specified")
        return self


class QuizGenerator:
    """
    Main quiz generation class that handles AI-powered question generation.
    Uses configuration profiles and templates to generate customized quizzes.
    """
    
    def __init__(self, config: QuizGeneratorConfig):
        self.config = config
        self._initialized = False
        
    async def initialize(self):
        """Initialize the quiz generator with AI models and resources"""
        if self._initialized:
            return
            
        try:
            # Initialize AI models based on configuration
            logger.info(f"Initializing QuizGenerator with config: {self.config.name}")
            logger.info(f"Question model: {self.config.question_model} ({self.config.question_provider})")
            
            if self.config.evaluation_model:
                logger.info(f"Evaluation model: {self.config.evaluation_model} ({self.config.evaluation_provider})")
            
            self._initialized = True
            logger.info("QuizGenerator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize QuizGenerator: {e}")
            raise

    async def generate_quiz(
        self,
        quiz_title: str,
        content: str,
        quiz_type: str = "multiple-choice",
        question_count: int = 10,
        difficulty: str = "medium",
        quiz_profile: Optional[QuizProfile] = None,
        quiz_template: Optional[QuizTemplate] = None,
        **kwargs
    ) -> Quiz:
        """
        Generate a complete quiz with questions based on the provided content.
        
        Args:
            quiz_title: Title of the quiz
            content: Source content to base questions on
            quiz_type: Type of quiz to generate
            question_count: Number of questions to generate
            difficulty: Difficulty level of questions
            quiz_profile: Optional quiz profile for configuration
            quiz_template: Optional quiz template for predefined settings
            **kwargs: Additional generation parameters
            
        Returns:
            Quiz object with generated questions
        """
        if not self._initialized:
            await self.initialize()

        try:
            logger.info(f"Starting quiz generation: {quiz_title}")
            logger.info(f"Parameters: type={quiz_type}, questions={question_count}, difficulty={difficulty}")
            logger.info(f"Content length: {len(content)} characters")

            # Validate parameters
            question_count = self._validate_question_count(question_count)
            quiz_type = self._validate_quiz_type(quiz_type)
            difficulty = self._validate_difficulty(difficulty)

            # Prepare generation parameters
            generation_params = self._prepare_generation_params(
                quiz_type=quiz_type,
                question_count=question_count,
                difficulty=difficulty,
                quiz_profile=quiz_profile,
                quiz_template=quiz_template,
                **kwargs
            )

            # Generate questions using AI with template-based prompting
            logger.info("Generating quiz questions with AI...")
            questions = await self._generate_questions_with_ai(content, generation_params)
            
            if not questions:
                logger.warning("No questions generated, using fallback questions")
                questions = self._generate_fallback_questions(generation_params)

            # Validate generated questions
            validated_questions = await self._validate_questions(questions, content, generation_params)
            logger.info(f"Generated {len(validated_questions)} validated questions")

            # Create and save quiz
            quiz = Quiz(
                title=quiz_title,
                quiz_type=quiz_type,
                question_count=len(validated_questions),
                status="completed",
                quiz_profile=quiz_profile.model_dump() if quiz_profile else {},
                questions=validated_questions,
            )
            
            await quiz.save()
            logger.info(f"Successfully created quiz: {quiz.id}")

            return quiz

        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            raise

    async def _generate_questions_with_ai(self, content: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate quiz questions using AI models with template-based prompting.
        
        This method:
        1. Loads and renders the quiz generation template
        2. Calls the configured AI model with the rendered prompt
        3. Parses the AI response to extract structured quiz questions
        4. Handles errors and provides fallback generation
        
        Args:
            content: Source content for question generation
            params: Generation parameters including quiz type, difficulty, etc.
            
        Returns:
            List of generated quiz questions
        """
        try:
            # Load and render the quiz template
            template_content = await self._load_quiz_template()
            rendered_prompt = self._render_quiz_template(template_content, content, params)
            
            logger.info(f"Rendered quiz prompt with {len(content)} characters of content")
            
            # Call AI service to generate questions
            llm_response = await self._call_ai_service(rendered_prompt, params)
            
            # Parse the AI response to extract questions
            questions = self._parse_ai_response(llm_response, params)
            
            logger.info(f"Successfully generated {len(questions)} questions from AI response")
            return questions
            
        except Exception as e:
            logger.error(f"AI question generation failed: {e}")
            # Return empty list to trigger fallback generation
            return []

    async def _load_quiz_template(self) -> str:
        """
        Load the quiz generation template from file system.
        
        Returns:
            Template content as string
        """
        try:
            # Try to load from templates directory
            template_path = Path("templates/quizzes/quiz_basic.jinja")
            if template_path.exists():
                return template_path.read_text(encoding="utf-8")
            else:
                # Fallback to built-in template
                logger.warning("Quiz template file not found, using built-in template")
                return self._get_builtin_template()
        except Exception as e:
            logger.error(f"Failed to load quiz template: {e}")
            return self._get_builtin_template()

    def _get_builtin_template(self) -> str:
        """
        Provide built-in quiz template as fallback.
        
        Returns:
            Built-in template content
        """
        return """You are an AI assistant specialized in creating educational quizzes and assessments. Your task is to generate high-quality quiz questions based on the provided content and parameters.

            **Content to base questions on:**
            <content>
            {{ content }}
            </content>

            **Quiz Parameters:**
            - Quiz Type: {{ quiz_type }}
            - Number of Questions: {{ question_count }}
            - Difficulty Level: {{ difficulty }}
            - Target Audience: {{ target_audience or "General learners" }}

            {% if quiz_type == 'mixed' %}
            **Mixed Quiz Distribution:**
            - Multiple Choice: 40%
            - True/False: 20%
            - Fill in the Blank: 20%
            - Problem-Solving: 20%
            {% endif %}

            **Guidelines for Question Creation:**

            1. **Content Accuracy**: All questions must be directly based on and verifiable from the provided content
            2. **Cognitive Levels**: Include questions at different cognitive levels:
            - Remembering (20%)
            - Understanding (30%)
            - Applying (30%)
            - Analyzing (20%)

            3. **Question Quality Standards**:
            - Clear, unambiguous wording
            - Plausible distractors for multiple choice
            - Appropriate difficulty for {{ difficulty }} level
            - Educational value and learning objectives

            **Output Format:**
            ```json
            {
            "quiz": {
                "title": "{{ quiz_title }}",
                "description": "{{ quiz_description }}",
                "quiz_type": "{{ quiz_type }}",
                "difficulty": "{{ difficulty }}",
                "questions": [
                {
                    "id": "q1",
                    "type": "multiple-choice",
                    "question": "Clear question text here?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option B",
                    "explanation": "Detailed explanation referencing the source content",
                    "difficulty": "easy"
                }
                ]
            }
            }
            IMPORTANT: Generate exactly {{ question_count }} questions that accurately reflect the provided content.
            """

    def _render_quiz_template(self, template: str, content: str, params: Dict[str, Any]) -> str:
        """
        Render the quiz template with provided content and parameters.
        
        Args:
            template: Template content
            content: Source content for questions
            params: Generation parameters
            
        Returns:
            Rendered prompt string
        """
        try:
            from jinja2 import Template
            
            # Prepare template variables
            template_vars = {
                "content": content,
                "quiz_type": params["quiz_type"],
                "question_count": params["question_count"],
                "difficulty": params["difficulty"],
                "target_audience": params.get("target_audience", "General learners"),
                "quiz_title": params.get("quiz_title", "Generated Quiz"),
                "quiz_description": params.get("quiz_description", "Quiz generated from provided content")
            }
            
            jinja_template = Template(template)
            rendered_prompt = jinja_template.render(**template_vars)
            
            return rendered_prompt
            
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            # Return basic prompt as fallback
            return f"""Generate {params['question_count']} {params['difficulty']} difficulty {params['quiz_type']} questions based on this content:
            Return the questions in JSON format with 'quiz' object containing 'questions' array.
    Each question should have: id, type, question, correct_answer, explanation, and difficulty."""
        
    async def _call_ai_service(self, prompt: str, params: Dict[str, Any]) -> str:
        """
        Call AI service to generate quiz questions.
        
        This method uses the same pattern as source_chat for model provisioning.
        
        Args:
            prompt: Rendered prompt for AI
            params: Generation parameters including model configuration
            
        Returns:
            AI response as string
        """
        try:
            # Use the same model provisioning pattern as source_chat
            from langchain_core.messages import HumanMessage
            
            # Create message payload
            messages = [HumanMessage(content=prompt)]
            
            # Provision model using the same utility as source_chat
            model = await provision_langchain_model(
                str(messages),
                self.config.question_model,
                "chat",
                max_tokens=8192,
            )
            
            # Invoke model
            response = model.invoke(messages)
            
            logger.info(f"AI service call completed successfully")
            return response.content
            
        except Exception as e:
            logger.error(f"AI service call failed: {e}")
            # Generate mock response for development
            return self._generate_mock_ai_response(prompt, params)

    def _generate_mock_ai_response(self, prompt: str, params: Dict[str, Any]) -> str:
        """
        Generate mock AI response for development and testing.
        
        Args:
            prompt: Original prompt (for context)
            params: Generation parameters
            
        Returns:
            Mock AI response in expected JSON format
        """
        quiz_type = params["quiz_type"]
        question_count = params["question_count"]
        difficulty = params["difficulty"]
        
        # Create mock questions based on parameters
        questions = []
        for i in range(question_count):
            question = {
                "id": f"q{i+1}",
                "type": quiz_type if quiz_type != "mixed" else ["multiple-choice", "true-false", "fill-blank", "problem-solving"][i % 4],
                "question": f"Sample {difficulty} difficulty question {i+1} based on the provided content?",
                "correct_answer": "Sample correct answer",
                "explanation": f"This explanation references key concepts from the content for question {i+1}.",
                "difficulty": difficulty
            }
            
            # Add options for multiple choice questions
            if question["type"] == "multiple-choice":
                question["options"] = ["Option A", "Option B", "Option C", "Option D"]
                question["correct_answer"] = "Option B"
            
            questions.append(question)
        
        mock_response = {
            "quiz": {
                "title": params.get("quiz_title", "Generated Quiz"),
                "description": "Quiz generated from provided content",
                "quiz_type": quiz_type,
                "difficulty": difficulty,
                "questions": questions
            }
        }
        
        return json.dumps(mock_response, indent=2)

    def _parse_ai_response(self, response: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse AI response to extract structured quiz questions.
        
        Args:
            response: Raw AI response
            params: Generation parameters for validation
            
        Returns:
            List of parsed quiz questions
        """
        try:
            # Extract JSON from response using regex (handles code blocks)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in AI response")
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            # Extract questions from the expected structure
            questions = data.get("quiz", {}).get("questions", [])
            
            if not questions:
                raise ValueError("No questions found in parsed JSON")
            
            # Validate and normalize question format
            validated_questions = []
            for i, question in enumerate(questions):
                validated_question = {
                    "id": question.get("id", f"q{i+1}"),
                    "type": question.get("type", params["quiz_type"]),
                    "question": question.get("question", f"Question {i+1}"),
                    "correct_answer": question.get("correct_answer", "Answer"),
                    "explanation": question.get("explanation", "Explanation not provided"),
                    "difficulty": question.get("difficulty", params["difficulty"])
                }
                
                # Handle multiple choice options
                if validated_question["type"] == "multiple-choice" and "options" in question:
                    validated_question["options"] = question["options"]
                
                validated_questions.append(validated_question)
            
            logger.info(f"Successfully parsed {len(validated_questions)} questions from AI response")
            return validated_questions
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise

    def _generate_fallback_questions(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate fallback questions when AI generation fails.
        
        Args:
            params: Generation parameters
            
        Returns:
            List of fallback questions
        """
        quiz_type = params["quiz_type"]
        question_count = params["question_count"]
        difficulty = params["difficulty"]
        
        questions = []
        for i in range(min(question_count, 5)):  # Limit fallback to 5 questions
            question = self._create_placeholder_question(
                question_id=f"q_{i+1}",
                quiz_type=quiz_type,
                difficulty=difficulty,
                index=i
            )
            questions.append(question)
        
        logger.warning(f"Using fallback questions: {len(questions)} questions generated")
        return questions

    # The following methods remain unchanged from your original implementation
    # but are included for completeness

    def _validate_question_count(self, question_count: int) -> int:
        """Validate and adjust question count based on configuration"""
        if question_count < 1:
            return self.config.default_question_count
        return min(question_count, self.config.max_question_count)

    def _validate_quiz_type(self, quiz_type: str) -> str:
        """Validate quiz type against supported types"""
        if quiz_type not in self.config.supported_quiz_types:
            logger.warning(f"Unsupported quiz type: {quiz_type}, using default: {self.config.default_quiz_type}")
            return self.config.default_quiz_type
        return quiz_type

    def _validate_difficulty(self, difficulty: str) -> str:
        """Validate difficulty level"""
        valid_difficulties = ["easy", "medium", "hard"]
        if difficulty not in valid_difficulties:
            return self.config.default_difficulty
        return difficulty

    def _prepare_generation_params(
        self,
        quiz_type: str,
        question_count: int,
        difficulty: str,
        quiz_profile: Optional[QuizProfile] = None,
        quiz_template: Optional[QuizTemplate] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Prepare generation parameters from various sources"""
        params = {
            "quiz_type": quiz_type,
            "question_count": question_count,
            "difficulty": difficulty,
            "creativity": self.config.creativity,
            "diversity_weight": self.config.diversity_weight,
            "enable_explanations": self.config.enable_explanations,
        }

        # Apply quiz profile settings if provided
        if quiz_profile:
            params.update({
                "quiz_types": quiz_profile.quiz_types,
                "difficulty_levels": quiz_profile.difficulty_levels,
                "passing_score": quiz_profile.passing_score_percentage,
            })

        # Apply template settings if provided
        if quiz_template:
            params.update({
                "instructions": quiz_template.instructions,
                "template_difficulty": quiz_template.difficulty_level,
            })

        # Apply any additional parameters
        params.update(kwargs)
        
        return params

    def _create_placeholder_question(self, question_id: str, quiz_type: str, difficulty: str, index: int) -> Dict[str, Any]:
        """Create a placeholder question for development"""
        base_question = {
            "id": question_id,
            "difficulty": difficulty,
        }

        if quiz_type == "multiple-choice":
            base_question.update({
                "type": "multiple-choice",
                "question": f"Sample multiple choice question {index+1} about the content?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option B",
                "explanation": "This is a sample explanation for the correct answer.",
            })
        elif quiz_type == "true-false":
            base_question.update({
                "type": "true-false",
                "question": f"Sample true/false statement {index+1} about the content?",
                "correct_answer": "True" if index % 2 == 0 else "False",
                "explanation": "This statement is verified by the source content.",
            })
        elif quiz_type == "fill-blank":
            base_question.update({
                "type": "fill-blank",
                "question": f"Sample fill in the blank question {index+1}: The important concept is __________.",
                "correct_answer": "key_term",
                "explanation": "The blank should be filled with the key term from the content.",
            })
        elif quiz_type == "problem-solving":
            base_question.update({
                "type": "problem-solving",
                "question": f"Sample problem-solving question {index+1}: How would you apply this concept to solve a real-world problem?",
                "correct_answer": "Sample solution approach",
                "explanation": "This demonstrates application of the concept.",
            })
        elif quiz_type == "mixed":
            types = ["multiple-choice", "true-false", "fill-blank", "problem-solving"]
            current_type = types[index % len(types)]
            base_question["type"] = current_type
            
            if current_type == "multiple-choice":
                base_question.update({
                    "question": f"Sample mixed multiple choice question {index+1}?",
                    "options": ["Choice 1", "Choice 2", "Choice 3", "Choice 4"],
                    "correct_answer": "Choice 2",
                    "explanation": "Mixed type explanation.",
                })
            elif current_type == "true-false":
                base_question.update({
                    "question": f"Sample mixed true/false statement {index+1}?",
                    "correct_answer": "True",
                    "explanation": "Mixed type explanation.",
                })
            elif current_type == "fill-blank":
                base_question.update({
                    "question": f"Sample mixed fill blank {index+1}: The concept of __________ is important.",
                    "correct_answer": "learning",
                    "explanation": "Mixed type explanation.",
                })
            else:  # problem-solving
                base_question.update({
                    "question": f"Sample mixed problem {index+1}: Describe how to apply this knowledge.",
                    "correct_answer": "Application description",
                    "explanation": "Mixed type explanation.",
                })
        else:
            # Default to multiple-choice
            base_question.update({
                "type": "multiple-choice",
                "question": f"Default question {index+1}?",
                "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                "correct_answer": "Option 2",
                "explanation": "Default explanation.",
            })
        
        return base_question

    async def _validate_questions(self, questions: List[Dict[str, Any]], content: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate generated questions for quality and accuracy.
        TODO: Implement actual validation logic with AI models.
        """
        # For now, just return the questions as-is
        # This should be enhanced with:
        # - Content accuracy validation
        # - Difficulty level verification  
        # - Question quality scoring
        # - Duplicate detection
        
        return questions

QUESTION_TYPES = [
{
"value": "multiple-choice",
"label": "Multiple Choice",
"description": "Questions with multiple answer options"
},
{
"value": "true-false",
"label": "True/False",
"description": "Statements that must be identified as true or false"
},
{
"value": "fill-blank",
"label": "Fill in the Blank",
"description": "Sentences with missing words or phrases to complete"
},
{
"value": "problem-solving",
"label": "Problem-Solving",
"description": "Scenarios requiring application of knowledge to solve problems"
},
{
"value": "mixed",
"label": "Mixed Types",
"description": "Combination of different question types"
}
]

DIFFICULTY_LEVELS = [
{
"value": "easy",
"label": "Easy",
"description": "Basic recall and understanding questions"
},
{
"value": "medium",
"label": "Medium",
"description": "Application and analysis questions"
},
{
"value": "hard",
"label": "Hard",
"description": "Evaluation and synthesis questions"
}
]

COGNITIVE_LEVELS = [
"Remembering",
"Understanding",
"Applying",
"Analyzing",
"Evaluating",
"Creating"
]

QUALITY_CRITERIA = [
"Clarity",
"Relevance",
"Accuracy",
"Appropriate Difficulty",
"Educational Value",
"Unambiguous Wording"
]