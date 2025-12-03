"""Core note matching engine with 7-tier matching strategy"""

import sqlite3
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from .name_matcher import NameMatcher
from .date_matcher import DateMatcher

logger = logging.getLogger(__name__)


@dataclass
class MatchCandidate:
    """Represents a potential Freed-Osmind note match"""
    freed_note_id: int
    osmind_note_id: int
    patient_id: int
    tier: int
    match_type: str
    confidence: float
    similarity_score: float
    freed_patient_name: str
    osmind_patient_name: str
    freed_visit_date: str
    osmind_visit_date: str


@dataclass
class MatchResults:
    """Summary of matching results"""
    total_freed: int
    total_osmind: int
    matched: int
    unmatched_freed: int
    tier_distribution: Dict[int, int]
    confidence_stats: Dict[str, float]
    matches: List[MatchCandidate]
    errors: List[str]


class NoteMatcher:
    """Main matching engine implementing 7-tier matching strategy"""

    # Tier configurations
    TIER_CONFIG = {
        1: {'name': 'exact_id_exact_date', 'confidence': 1.00, 'auto_match': True},
        2: {'name': 'exact_id_date_tolerance', 'confidence': 0.95, 'auto_match': True},
        3: {'name': 'exact_name_exact_date', 'confidence': 0.90, 'auto_match': True},
        4: {'name': 'fuzzy_name_exact_date', 'confidence': 0.85, 'auto_match': True},
        5: {'name': 'exact_name_date_tolerance', 'confidence': 0.80, 'auto_match': True},
        6: {'name': 'fuzzy_name_date_tolerance', 'confidence': 0.70, 'auto_match': True},  # Per user: 0.70 threshold
        7: {'name': 'partial_name_exact_date', 'confidence': 0.60, 'auto_match': False},  # Manual review
    }

    # Similarity thresholds
    TIER_4_THRESHOLD = 0.90  # Fuzzy name
    TIER_6_THRESHOLD = 0.85  # Fuzzy name with date tolerance
    TIER_7_THRESHOLD = 0.70  # Partial name

    def __init__(self, db_path: str, skip_existing: bool = True,
                 skip_has_freed_content: bool = True, auto_match_threshold: float = 0.70,
                 min_tier: int = 1):
        """Initialize note matcher

        Args:
            db_path: Path to SQLite database
            skip_existing: Skip notes already in combined_notes (default: True)
            skip_has_freed_content: Skip Osmind notes with has_freed_content=1 (default: True)
            auto_match_threshold: Minimum confidence for auto-matching (default: 0.70)
            min_tier: Minimum tier to start matching from (default: 1, use all tiers)
        """
        self.db_path = db_path
        self.skip_existing = skip_existing
        self.skip_has_freed_content = skip_has_freed_content
        self.auto_match_threshold = auto_match_threshold
        self.min_tier = min_tier

        self.name_matcher = NameMatcher()
        self.date_matcher = DateMatcher()

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def match_all_notes(self, tier_limit: int = 7, dry_run: bool = False) -> MatchResults:
        """Match all Freed notes to Osmind notes using 7-tier strategy

        Args:
            tier_limit: Maximum tier to use (1-7, default: 7)
            dry_run: If True, don't create database records (default: False)

        Returns:
            MatchResults with statistics and matched pairs
        """
        logger.info(f"Starting fuzzy matching (tier_limit={tier_limit}, dry_run={dry_run})")

        # Load Freed and Osmind notes
        freed_notes = self._load_freed_notes()
        osmind_notes = self._load_osmind_notes()

        logger.info(f"Loaded {len(freed_notes)} Freed notes, {len(osmind_notes)} Osmind notes")

        matches = []
        errors = []
        tier_distribution = {i: 0 for i in range(1, tier_limit + 1)}

        # Process each Freed note through tier matching
        for freed_note in freed_notes:
            try:
                match = self._match_single_note(freed_note, osmind_notes, tier_limit)

                if match:
                    matches.append(match)
                    tier_distribution[match.tier] += 1

                    # Create database record if not dry run and auto-match eligible
                    if not dry_run and match.confidence >= self.auto_match_threshold:
                        self._create_combined_note(match)
                        logger.info(f"Matched Freed#{match.freed_note_id} → Osmind#{match.osmind_note_id} "
                                  f"(Tier {match.tier}, {match.confidence:.1%} confidence)")
                    elif not dry_run:
                        # Low confidence - flag for manual review
                        self._create_combined_note(match, manual_review=True)
                        logger.warning(f"Low confidence match Freed#{match.freed_note_id} → Osmind#{match.osmind_note_id} "
                                     f"(Tier {match.tier}, {match.confidence:.1%} confidence) - flagged for review")

            except Exception as e:
                error_msg = f"Error matching Freed note {freed_note['id']}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Calculate statistics
        confidence_scores = [m.confidence for m in matches]
        confidence_stats = {
            'avg': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0,
            'min': min(confidence_scores) if confidence_scores else 0.0,
            'max': max(confidence_scores) if confidence_scores else 0.0,
        }

        results = MatchResults(
            total_freed=len(freed_notes),
            total_osmind=len(osmind_notes),
            matched=len(matches),
            unmatched_freed=len(freed_notes) - len(matches),
            tier_distribution=tier_distribution,
            confidence_stats=confidence_stats,
            matches=matches,
            errors=errors
        )

        logger.info(f"Matching complete: {results.matched}/{results.total_freed} matched "
                   f"({results.matched/results.total_freed*100:.1%})")

        return results

    def _load_freed_notes(self) -> List[Dict]:
        """Load Freed notes that need matching"""
        query = """
            SELECT
                fn.id,
                fn.patient_id,
                fn.visit_date,
                fn.note_text,
                p.name as patient_name,
                p.freed_patient_id,
                p.osmind_patient_id
            FROM freed_notes fn
            JOIN patients p ON fn.patient_id = p.id
        """

        if self.skip_existing:
            query += """
                WHERE fn.id NOT IN (
                    SELECT freed_note_id FROM combined_notes
                    WHERE freed_note_id IS NOT NULL
                )
            """

        self.cursor.execute(query)
        return [dict(row) for row in self.cursor.fetchall()]

    def _load_osmind_notes(self) -> List[Dict]:
        """Load Osmind notes available for matching"""
        query = """
            SELECT
                osm.id,
                osm.patient_id,
                osm.visit_date,
                osm.note_text,
                osm.patient_name,
                osm.has_freed_content,
                osm.osmind_note_id,
                osm.osmind_patient_id,
                p.freed_patient_id,
                p.osmind_patient_id as patient_osmind_id
            FROM osmind_notes osm
            JOIN patients p ON osm.patient_id = p.id
        """

        conditions = []
        if self.skip_has_freed_content:
            conditions.append("(osm.has_freed_content = 0 OR osm.has_freed_content IS NULL)")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        self.cursor.execute(query)
        return [dict(row) for row in self.cursor.fetchall()]

    def _match_single_note(self, freed_note: Dict, osmind_notes: List[Dict], tier_limit: int) -> Optional[MatchCandidate]:
        """Match a single Freed note through tier strategy

        Args:
            freed_note: Freed note dictionary
            osmind_notes: List of Osmind notes
            tier_limit: Maximum tier to use

        Returns:
            Best match candidate or None
        """
        # Try each tier in order, starting from min_tier
        for tier in range(self.min_tier, tier_limit + 1):
            candidates = self._find_candidates(freed_note, osmind_notes, tier)

            if candidates:
                # Return best candidate from this tier
                best = max(candidates, key=lambda c: c.similarity_score)
                return best

        return None

    def _find_candidates(self, freed_note: Dict, osmind_notes: List[Dict], tier: int) -> List[MatchCandidate]:
        """Find matching candidates for a specific tier

        Args:
            freed_note: Freed note dictionary
            osmind_notes: List of Osmind notes
            tier: Tier number (1-7)

        Returns:
            List of matching candidates for this tier
        """
        candidates = []

        for osmind_note in osmind_notes:
            match = self._score_match(freed_note, osmind_note, tier)
            if match:
                candidates.append(match)

        return candidates

    def _score_match(self, freed: Dict, osmind: Dict, tier: int) -> Optional[MatchCandidate]:
        """Score a potential match for a specific tier

        Returns MatchCandidate if match qualifies for tier, else None
        """
        tier_config = self.TIER_CONFIG[tier]

        # Tier 1: Exact Patient ID + Exact Date
        if tier == 1:
            if freed['osmind_patient_id'] and freed['osmind_patient_id'] == osmind['patient_osmind_id']:
                if self.date_matcher.is_same_date(freed['visit_date'], osmind['visit_date']):
                    return MatchCandidate(
                        freed_note_id=freed['id'],
                        osmind_note_id=osmind['id'],
                        patient_id=freed['patient_id'],
                        tier=1,
                        match_type='exact_id_exact_date',
                        confidence=1.00,
                        similarity_score=1.00,
                        freed_patient_name=freed['patient_name'],
                        osmind_patient_name=osmind['patient_name'],
                        freed_visit_date=freed['visit_date'],
                        osmind_visit_date=osmind['visit_date']
                    )

        # Tier 2: Exact Patient ID + Date ±1 day
        elif tier == 2:
            if freed['osmind_patient_id'] and freed['osmind_patient_id'] == osmind['patient_osmind_id']:
                if self.date_matcher.within_tolerance(freed['visit_date'], osmind['visit_date'], days=1):
                    return MatchCandidate(
                        freed_note_id=freed['id'],
                        osmind_note_id=osmind['id'],
                        patient_id=freed['patient_id'],
                        tier=2,
                        match_type='exact_id_date_tolerance',
                        confidence=0.95,
                        similarity_score=0.95,
                        freed_patient_name=freed['patient_name'],
                        osmind_patient_name=osmind['patient_name'],
                        freed_visit_date=freed['visit_date'],
                        osmind_visit_date=osmind['visit_date']
                    )

        # Tier 3: Exact Name + Exact Date
        elif tier == 3:
            if self.name_matcher.is_exact_match(freed['patient_name'], osmind['patient_name']):
                if self.date_matcher.is_same_date(freed['visit_date'], osmind['visit_date']):
                    similarity = self.name_matcher.calculate_similarity(freed['patient_name'], osmind['patient_name'])
                    return MatchCandidate(
                        freed_note_id=freed['id'],
                        osmind_note_id=osmind['id'],
                        patient_id=freed['patient_id'],
                        tier=3,
                        match_type='exact_name_exact_date',
                        confidence=0.90,
                        similarity_score=similarity,
                        freed_patient_name=freed['patient_name'],
                        osmind_patient_name=osmind['patient_name'],
                        freed_visit_date=freed['visit_date'],
                        osmind_visit_date=osmind['visit_date']
                    )

        # Tier 4: Fuzzy Name (>90%) + Exact Date
        elif tier == 4:
            similarity = self.name_matcher.calculate_similarity(freed['patient_name'], osmind['patient_name'])
            if similarity > self.TIER_4_THRESHOLD:
                if self.date_matcher.is_same_date(freed['visit_date'], osmind['visit_date']):
                    return MatchCandidate(
                        freed_note_id=freed['id'],
                        osmind_note_id=osmind['id'],
                        patient_id=freed['patient_id'],
                        tier=4,
                        match_type='fuzzy_name_exact_date',
                        confidence=0.85,
                        similarity_score=similarity,
                        freed_patient_name=freed['patient_name'],
                        osmind_patient_name=osmind['patient_name'],
                        freed_visit_date=freed['visit_date'],
                        osmind_visit_date=osmind['visit_date']
                    )

        # Tier 5: Exact Name + Date ±1 day
        elif tier == 5:
            if self.name_matcher.is_exact_match(freed['patient_name'], osmind['patient_name']):
                if self.date_matcher.within_tolerance(freed['visit_date'], osmind['visit_date'], days=1):
                    similarity = self.name_matcher.calculate_similarity(freed['patient_name'], osmind['patient_name'])
                    return MatchCandidate(
                        freed_note_id=freed['id'],
                        osmind_note_id=osmind['id'],
                        patient_id=freed['patient_id'],
                        tier=5,
                        match_type='exact_name_date_tolerance',
                        confidence=0.80,
                        similarity_score=similarity,
                        freed_patient_name=freed['patient_name'],
                        osmind_patient_name=osmind['patient_name'],
                        freed_visit_date=freed['visit_date'],
                        osmind_visit_date=osmind['visit_date']
                    )

        # Tier 6: Fuzzy Name (>85%) + Date ±1 day
        elif tier == 6:
            similarity = self.name_matcher.calculate_similarity(freed['patient_name'], osmind['patient_name'])
            if similarity > self.TIER_6_THRESHOLD:
                if self.date_matcher.within_tolerance(freed['visit_date'], osmind['visit_date'], days=1):
                    return MatchCandidate(
                        freed_note_id=freed['id'],
                        osmind_note_id=osmind['id'],
                        patient_id=freed['patient_id'],
                        tier=6,
                        match_type='fuzzy_name_date_tolerance',
                        confidence=0.70,
                        similarity_score=similarity,
                        freed_patient_name=freed['patient_name'],
                        osmind_patient_name=osmind['patient_name'],
                        freed_visit_date=freed['visit_date'],
                        osmind_visit_date=osmind['visit_date']
                    )

        # Tier 7: Partial Name (First OR Last) + Exact Date
        elif tier == 7:
            matches, partial_sim = self.name_matcher.partial_match(freed['patient_name'], osmind['patient_name'])
            if matches and partial_sim > self.TIER_7_THRESHOLD:
                if self.date_matcher.is_same_date(freed['visit_date'], osmind['visit_date']):
                    return MatchCandidate(
                        freed_note_id=freed['id'],
                        osmind_note_id=osmind['id'],
                        patient_id=freed['patient_id'],
                        tier=7,
                        match_type='partial_name_exact_date',
                        confidence=0.60,
                        similarity_score=partial_sim,
                        freed_patient_name=freed['patient_name'],
                        osmind_patient_name=osmind['patient_name'],
                        freed_visit_date=freed['visit_date'],
                        osmind_visit_date=osmind['visit_date']
                    )

        return None

    def _create_combined_note(self, match: MatchCandidate, manual_review: bool = False) -> int:
        """Create combined_notes record from match

        Args:
            match: Match candidate
            manual_review: Flag for manual review (default: False)

        Returns:
            ID of created combined_note
        """
        # Determine sync status
        if manual_review or match.confidence < self.auto_match_threshold:
            sync_status = 'manual_review'
            manual_match = True
        else:
            sync_status = 'matched'
            manual_match = False

        # Get original note text
        self.cursor.execute("SELECT note_text FROM freed_notes WHERE id = ?", (match.freed_note_id,))
        row = self.cursor.fetchone()
        original_note = row['note_text'] if row else None

        # Insert combined note with match quality tracking
        self.cursor.execute("""
            INSERT INTO combined_notes
            (patient_id, visit_date, freed_note_id, osmind_note_id,
             original_freed_note, sync_status, manual_match,
             match_tier, match_confidence, match_type, similarity_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match.patient_id,
            match.freed_visit_date,
            match.freed_note_id,
            match.osmind_note_id,
            original_note,
            sync_status,
            manual_match,
            str(match.tier),
            match.confidence,
            match.match_type,
            match.similarity_score
        ))

        self.conn.commit()
        return self.cursor.lastrowid

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
