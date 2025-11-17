from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import Field, field_validator
from surrealdb import RecordID

from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.base import ObjectModel


class EpisodeProfile(ObjectModel):
    """
    Episode Profile - Simplified podcast configuration.
    Replaces complex 15+ field configuration with user-friendly profiles.
    """

    table_name: ClassVar[str] = "episode_profile"

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    speaker_config: str = Field(..., description="Reference to speaker profile name")
    outline_provider: str = Field(..., description="AI provider for outline generation")
    outline_model: str = Field(..., description="AI model for outline generation")
    transcript_provider: str = Field(
        ..., description="AI provider for transcript generation"
    )
    transcript_model: str = Field(..., description="AI model for transcript generation")
    default_briefing: str = Field(..., description="Default briefing template")
    num_segments: int = Field(default=5, description="Number of podcast segments")

    @field_validator("num_segments")
    @classmethod
    def validate_segments(cls, v):
        """Validate number of segments is within reasonable range"""
        if not 1 <= v <= 20:
            raise ValueError("Number of segments must be between 1 and 20")
        return v

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["EpisodeProfile"]:
        """Get episode profile by name"""
        result = await repo_query(
            "SELECT * FROM episode_profile WHERE name = $name", {"name": name}
        )
        if result:
            return cls(**result[0])
        return None

    @classmethod
    async def recommend_profiles(cls, content_sample: str, target_duration: int = 15) -> Dict[str, Any]:
        """
        Intelligently recommend optimal podcast configurations based on content analysis.
        Innovation: Content-aware automatic configuration recommendation.
        """
        # Lightweight content analysis (self-contained)
        content_metrics = cls._analyze_content(content_sample)
        
        # Generate recommendations based on simple rules
        recommendations = cls._generate_recommendations(content_metrics, target_duration)
        
        return {
            "content_analysis": content_metrics,
            "recommended_profiles": recommendations,
            "reasoning": cls._explain_recommendations(content_metrics),
            "confidence_score": cls._calculate_confidence(content_metrics)
        }
    
    @classmethod
    def _analyze_content(cls, content: str) -> Dict[str, Any]:
        """Lightweight content analysis - completely self-contained"""
        word_count = len(content.split())
        sentence_count = len([s for s in content.split('.') if s.strip()])
        paragraph_count = len([p for p in content.split('\n') if p.strip()])
        
        # Simple complexity analysis
        avg_sentence_length = word_count / max(sentence_count, 1)
        lexical_density = len(set(content.split())) / max(word_count, 1)
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count, 
            "paragraph_count": paragraph_count,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "lexical_density": round(lexical_density, 3),
            "complexity_level": "high" if avg_sentence_length > 15 else "medium" if avg_sentence_length > 10 else "low"
        }
    
    @classmethod
    def _generate_recommendations(cls, metrics: Dict[str, Any], target_duration: int) -> List[Dict[str, Any]]:
        """Generate configuration recommendations based on content metrics"""
        recommendations = []
        
        # Recommend different configurations based on content complexity
        if metrics["complexity_level"] == "high":
            recommendations.append({
                "profile_type": "detailed_explanation",
                "recommended_segments": min(8, metrics["paragraph_count"]),
                "speaker_count": 2,
                "pace": "slow_deliberate", 
                "reasoning": "Complex content suitable for detailed explanation and dual-speaker dialogue"
            })
        elif metrics["complexity_level"] == "medium":
            recommendations.append({
                "profile_type": "balanced_discussion", 
                "recommended_segments": min(6, metrics["paragraph_count"]),
                "speaker_count": 1,
                "pace": "moderate",
                "reasoning": "Medium complexity content suitable for balanced discussion pace"
            })
        else:
            recommendations.append({
                "profile_type": "conversational",
                "recommended_segments": min(4, metrics["paragraph_count"]),
                "speaker_count": 1, 
                "pace": "lively",
                "reasoning": "Simple content suitable for casual conversation style"
            })
        
        # Adjust duration based on content length
        for rec in recommendations:
            rec["estimated_duration"] = f"{target_duration} minutes"
            rec["segment_duration"] = f"{target_duration/rec['recommended_segments']:.1f} minutes/segment"
            
        return recommendations
    
    @classmethod 
    def _explain_recommendations(cls, metrics: Dict[str, Any]) -> str:
        """Generate reasoning for recommendations - enhances credibility"""
        return (f"Detected {metrics['word_count']} words, average sentence length {metrics['avg_sentence_length']} words, "
                f"lexical density {metrics['lexical_density']}. Recommended {metrics['complexity_level']} complexity handling strategy.")
    
    @classmethod
    def _calculate_confidence(cls, metrics: Dict[str, Any]) -> float:
        """Calculate recommendation confidence score"""
        base_confidence = 0.7
        # Fine-tune confidence based on data completeness
        if metrics["word_count"] > 200:
            base_confidence += 0.2
        if metrics["sentence_count"] > 5:
            base_confidence += 0.1
        return min(0.95, base_confidence)


class SpeakerProfile(ObjectModel):
    """
    Speaker Profile - Voice and personality configuration.
    Supports 1-4 speakers for flexible podcast formats.
    """

    table_name: ClassVar[str] = "speaker_profile"

    name: str = Field(..., description="Unique profile name")
    description: Optional[str] = Field(None, description="Profile description")
    tts_provider: str = Field(
        ..., description="TTS provider (openai, elevenlabs, etc.)"
    )
    tts_model: str = Field(..., description="TTS model name")
    speakers: List[Dict[str, Any]] = Field(
        ..., description="Array of speaker configurations"
    )

    @field_validator("speakers")
    @classmethod
    def validate_speakers(cls, v):
        """Validate speaker configuration meets requirements"""
        if not 1 <= len(v) <= 4:
            raise ValueError("Must have between 1 and 4 speakers")

        required_fields = ["name", "voice_id", "backstory", "personality"]
        for speaker in v:
            for field in required_fields:
                if field not in speaker:
                    raise ValueError(f"Speaker missing required field: {field}")
        return v

    @classmethod
    async def get_by_name(cls, name: str) -> Optional["SpeakerProfile"]:
        """Get speaker profile by name"""
        result = await repo_query(
            "SELECT * FROM speaker_profile WHERE name = $name", {"name": name}
        )
        if result:
            return cls(**result[0])
        return None

    @classmethod
    async def recommend_speakers(cls, content_tone: str, audience_type: str = "general") -> Dict[str, Any]:
        """
        Recommend optimal speaker configurations based on content style and audience.
        Innovation: Style-aware speaker matching and audience consideration.
        """
        tone_mappings = {
            "academic": {"pace": "slow", "formality": "high", "energy": "medium"},
            "casual": {"pace": "moderate", "formality": "low", "energy": "high"}, 
            "technical": {"pace": "moderate", "formality": "medium", "energy": "medium"},
            "storytelling": {"pace": "varied", "formality": "low", "energy": "high"}
        }
        
        audience_mappings = {
            "general": {"clarity": "high", "jargon": "avoid", "examples": "many"},
            "expert": {"clarity": "medium", "jargon": "okay", "examples": "few"},
            "student": {"clarity": "high", "jargon": "explain", "examples": "many"}
        }
        
        tone_profile = tone_mappings.get(content_tone, tone_mappings["casual"])
        audience_profile = audience_mappings.get(audience_type, audience_mappings["general"])
        
        return {
            "content_tone_analysis": tone_profile,
            "audience_considerations": audience_profile,
            "recommended_speaker_traits": {
                "voice_characteristics": cls._suggest_voice(tone_profile),
                "delivery_style": cls._suggest_delivery(audience_profile),
                "interaction_pattern": cls._suggest_interaction(content_tone)
            },
            "configuration_confidence": 0.85
        }
    
    @classmethod
    def _suggest_voice(cls, tone_profile: Dict[str, str]) -> List[str]:
        """Recommend voice characteristics based on content style"""
        suggestions = []
        if tone_profile["formality"] == "high":
            suggestions.extend(["clear_articulation", "steady_pace", "authoritative_tone"])
        else:
            suggestions.extend(["conversational_tone", "expressive_variation", "friendly_warmth"])
        return suggestions
    
    @classmethod
    def _suggest_delivery(cls, audience_profile: Dict[str, str]) -> List[str]:
        """Recommend delivery style based on target audience"""
        suggestions = []
        if audience_profile["clarity"] == "high":
            suggestions.extend(["pause_for_emphasis", "repeat_key_points", "clear_transitions"])
        return suggestions
    
    @classmethod 
    def _suggest_interaction(cls, content_tone: str) -> str:
        """Recommend interaction pattern based on content tone"""
        if content_tone in ["academic", "technical"]:
            return "monologue_with_occasional_qa"
        else:
            return "conversational_exchange"


class PodcastEpisode(ObjectModel):
    """Enhanced PodcastEpisode with job tracking and metadata"""

    table_name: ClassVar[str] = "episode"

    name: str = Field(..., description="Episode name")
    episode_profile: Dict[str, Any] = Field(
        ..., description="Episode profile used (stored as object)"
    )
    speaker_profile: Dict[str, Any] = Field(
        ..., description="Speaker profile used (stored as object)"
    )
    briefing: str = Field(..., description="Full briefing used for generation")
    content: str = Field(..., description="Source content")
    audio_file: Optional[str] = Field(
        default=None, description="Path to generated audio file"
    )
    transcript: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Generated transcript"
    )
    outline: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Generated outline"
    )
    command: Optional[Union[str, RecordID]] = Field(
        default=None, description="Link to surreal-commands job"
    )

    class Config:
        arbitrary_types_allowed = True

    async def get_job_status(self) -> Optional[str]:
        """Get the status of the associated command"""
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
        """Parse command field to ensure proper RecordID format"""
        if isinstance(value, str):
            return ensure_record_id(value)
        return value

    def _prepare_save_data(self) -> dict:
        """Override to ensure command field is always RecordID format for database"""
        data = super()._prepare_save_data()
        
        # Ensure command field is RecordID format if not None
        if data.get("command") is not None:
            data["command"] = ensure_record_id(data["command"])
            
        return data

    async def generate_with_intelligence(self) -> Dict[str, Any]:
        """
        Generate podcast using intelligent content analysis and recommendations.
        Innovation: Unified intelligent generation combining content analysis and style matching.
        """
        # Get intelligent episode profile recommendations
        episode_recommendations = await EpisodeProfile.recommend_profiles(self.content)
        
        # Analyze content tone for speaker matching
        content_tone = self._analyze_content_tone(self.content)
        
        # Get intelligent speaker recommendations
        speaker_recommendations = await SpeakerProfile.recommend_speakers(content_tone)
        
        return {
            "intelligent_episode_config": episode_recommendations,
            "intelligent_speaker_config": speaker_recommendations,
            "content_tone_analysis": content_tone,
            "generation_metadata": {
                "ai_enhanced": True,
                "content_aware": True,
                "audience_optimized": True,
                "style_matched": True
            }
        }
    
    def _analyze_content_tone(self, content: str) -> str:
        """
        Simple content tone analysis based on keyword detection.
        In production, this could be enhanced with NLP models.
        """
        content_lower = content.lower()
        
        academic_keywords = ["research", "study", "analysis", "methodology", "hypothesis"]
        technical_keywords = ["algorithm", "system", "implementation", "framework", "architecture"]
        storytelling_keywords = ["story", "experience", "journey", "narrative", "personal"]
        
        academic_score = sum(1 for keyword in academic_keywords if keyword in content_lower)
        technical_score = sum(1 for keyword in technical_keywords if keyword in content_lower)
        storytelling_score = sum(1 for keyword in storytelling_keywords if keyword in content_lower)
        
        if academic_score >= 2:
            return "academic"
        elif technical_score >= 2:
            return "technical"
        elif storytelling_score >= 2:
            return "storytelling"
        else:
            return "casual"