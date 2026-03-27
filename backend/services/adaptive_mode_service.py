"""
Adaptive tutoring mode selection service.
Central place for deciding how the tutor should teach.
"""

import logging
from typing import Dict, Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

TUTORING_MODES = {
    'direct',
    'supportive',
    'socratic',
    'supportive_socratic',
}


class AdaptiveModeService:
    """Decide tutoring mode from learner signals."""

    @staticmethod
    def normalize_level(level: Optional[str]) -> str:
        lvl = (level or 'intermediate').strip().lower()
        if lvl in ('beginner', 'intermediate', 'advanced'):
            return lvl
        return 'intermediate'

    @staticmethod
    def decide_mode(
        learner_level: Optional[str] = None,
        uncertainty_markers: int = 0,
        misconception_detected: bool = False,
        emotional_state: str = 'neutral',
        low_mastery_detected: bool = False,
        user_preference: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Returns (mode, reason).

        user_preference can be one of: direct, guided, supportive.
        """
        pref = (user_preference or '').strip().lower()
        needs_support = False
        needs_socratic = False
        reasons = []

        level = AdaptiveModeService.normalize_level(learner_level)
        if level == 'beginner':
            needs_support = True
            reasons.append('beginner level learner')

        if uncertainty_markers >= 1:
            needs_support = True
            needs_socratic = True
            reasons.append('uncertainty detected')

        if misconception_detected:
            needs_support = True
            needs_socratic = True
            reasons.append('misconception detected')

        emo = (emotional_state or 'neutral').lower()
        if emo in ('frustrated', 'confused'):
            needs_support = True
            reasons.append(f'{emo} emotional state')
        elif emo == 'curious':
            needs_socratic = True
            reasons.append('curiosity detected')

        if low_mastery_detected:
            needs_support = True
            reasons.append('low mastery signal')

        # Preference is a nudge, not a hard override against active support/socratic needs.
        if pref == 'guided':
            needs_socratic = True
            reasons.append('user preference: more guided')
        elif pref == 'supportive':
            needs_support = True
            reasons.append('user preference: more supportive')
        elif pref == 'direct' and not needs_support and not needs_socratic:
            return 'direct', 'user preference: more direct'

        if needs_support and needs_socratic:
            mode = 'supportive_socratic'
        elif needs_socratic:
            mode = 'socratic'
        elif needs_support:
            mode = 'supportive'
        else:
            mode = 'direct'

        reason = '; '.join(reasons) if reasons else 'stable understanding detected'
        logger.debug(
            "AdaptiveModeService.decide_mode -> mode=%s reason=%s support=%s socratic=%s level=%s uncertainty=%s misconception=%s emotion=%s low_mastery=%s pref=%s",
            mode,
            reason,
            needs_support,
            needs_socratic,
            level,
            uncertainty_markers,
            misconception_detected,
            emo,
            low_mastery_detected,
            pref,
        )
        return mode, reason

    @staticmethod
    def is_socratic(mode: str) -> bool:
        return mode in ('socratic', 'supportive_socratic')

    @staticmethod
    def mode_prompt_instruction(mode: str) -> str:
        if mode == 'supportive':
            return (
                'MODE: SUPPORTIVE. Use warm encouragement, reduce frustration, '
                'break explanations into small clear steps, and reassure progress. '
                'Do NOT use guiding Socratic questions in this mode.'
            )
        if mode == 'socratic':
            return (
                'MODE: SOCRATIC. Prefer guiding questions first, let the learner reason, '
                'then confirm or correct with concise explanations.'
            )
        if mode == 'supportive_socratic':
            return (
                'MODE: SUPPORTIVE_SOCRATIC. Be encouraging and patient while using '
                'guiding questions before direct explanations.'
            )
        return (
            'MODE: DIRECT. Give clear, efficient explanations with minimal detours, '
            'while still staying polite and accurate.'
        )

    @staticmethod
    def has_low_mastery(topics_map: Dict, topics: Iterable[str]) -> bool:
        for topic in topics or []:
            td = topics_map.get(topic, {}) if isinstance(topics_map, dict) else {}
            mastery = td.get('mastery_level', 1.0) if isinstance(td, dict) else 1.0
            count = td.get('count', 0) if isinstance(td, dict) else 0
            if count >= 2 and mastery < 0.45:
                return True
        return False
