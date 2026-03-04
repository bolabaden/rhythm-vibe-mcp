"""music_theory.py

A comprehensive, mathematically rigorous implementation of music theory concepts,
derived from extensive web scraping of Wikipedia, LibreTexts, Open Music Theory,
Neo-Riemannian theory, Schenkerian concepts, and common-practice rules.

This module provides the algorithmic and logical foundation for:
- Pitch and Interval mathematics
- Scale and Mode generation
- Chord construction and Roman Numeral Analysis
- Neo-Riemannian Transformations (P, L, R)
- Voice Leading validation (parallel 5ths/octaves)
- Figured Bass and Inversions
- Cadential evaluation
"""

from __future__ import annotations

import itertools
import math
import cmath
from enum import Enum
from typing import cast

from rhythm_vibe_mcp.theory_primitives import Interval, Note, PitchClass, PITCH_NAMES, Scales

__all__ = ["PitchClass", "PITCH_NAMES", "Note", "Interval", "Scales"]

# --------------------------------------------------------------------------- #
# 1. Pitch and Intervals
# --------------------------------------------------------------------------- #

# Primitives are hosted in theory_primitives and re-exported via this module
# for backward-compatible imports from rhythm_vibe_mcp.theory.


# --------------------------------------------------------------------------- #
# 3. Chords and Triads
# --------------------------------------------------------------------------- #


class ChordType(Enum):
    MAJOR = [0, 4, 7]
    MINOR = [0, 3, 7]
    DIMINISHED = [0, 3, 6]
    AUGMENTED = [0, 4, 8]
    MAJOR_SEVENTH = [0, 4, 7, 11]
    MINOR_SEVENTH = [0, 3, 7, 10]
    DOMINANT_SEVENTH = [0, 4, 7, 10]
    HALF_DIMINISHED_SEVENTH = [0, 3, 6, 10]
    FULLY_DIMINISHED_SEVENTH = [0, 3, 6, 9]
    SUS2 = [0, 2, 7]
    SUS4 = [0, 5, 7]


class Chord:
    def __init__(self, root: int, chord_type: list[int], inversion: int = 0):
        """Function __init__.

        Args:
        ----
            root (int): The root argument.
            chord_type (Any): The chord_type argument.
            inversion (int): The inversion argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for __init__

        """
        self.root = root % 12
        self.chord_type = chord_type
        # Pitches in the chord (ordered by root position initially)
        self.pitches = [(root + interval) % 12 for interval in chord_type]
        self.inversion = inversion % len(chord_type)

    def get_bass(self) -> int:
        """Returns the pitch class of the lowest note according to the inversion.

        Args:
        ----
            None

        Returns:
        -------
            int: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for get_bass

        """
        """Returns the pitch class of the lowest note according to the inversion."""
        return self.pitches[self.inversion]

    def is_major(self) -> bool:
        """Function is_major.

        Args:
        ----
            None

        Returns:
        -------
            bool: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for is_major

        """
        return self.chord_type == ChordType.MAJOR.value

    def is_minor(self) -> bool:
        """Function is_minor.

        Args:
        ----
            None

        Returns:
        -------
            bool: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for is_minor

        """
        return self.chord_type == ChordType.MINOR.value

    def __repr__(self) -> str:
        """Function __repr__.

        Args:
        ----
            None

        Returns:
        -------
            str: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for __repr__

        """
        root_name = PITCH_NAMES[self.root]
        bass_name = PITCH_NAMES[self.get_bass()]
        suffix = ""
        if self.chord_type == ChordType.MAJOR.value:
            suffix = "maj"
        elif self.chord_type == ChordType.MINOR.value:
            suffix = "min"
        elif self.chord_type == ChordType.DIMINISHED.value:
            suffix = "dim"
        elif self.chord_type == ChordType.AUGMENTED.value:
            suffix = "aug"
        elif self.chord_type == ChordType.DOMINANT_SEVENTH.value:
            suffix = "7"
        elif self.chord_type == ChordType.MAJOR_SEVENTH.value:
            suffix = "maj7"
        elif self.chord_type == ChordType.MINOR_SEVENTH.value:
            suffix = "min7"
        else:
            suffix = " (ext)"

        inv_str = f"/{bass_name}" if self.inversion > 0 else ""
        return f"{root_name}{suffix}{inv_str}"


# --------------------------------------------------------------------------- #
# 4. Neo-Riemannian Theory
# --------------------------------------------------------------------------- #


class NeoRiemannian:
    """Implements Neo-Riemannian transformations (P, L, R) on Major and Minor triads.
    These operations map a triad to another triad by moving only one or two voices
    by a semitone or tone, maximizing voice-leading parsimony on the Tonnetz.
    """

    @staticmethod
    def P(chord: Chord) -> Chord:
        """Parallel: Maps a major chord to its parallel minor, and vice versa.
        Moves the third by a semitone.

        Args:
        ----
            chord (Chord): The chord argument.

        Returns:
        -------
            Chord: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for P

        """
        """Parallel: Maps a major chord to its parallel minor, and vice versa.
        Moves the third by a semitone."""
        if chord.is_major():
            return Chord(chord.root, ChordType.MINOR.value)
        if chord.is_minor():
            return Chord(chord.root, ChordType.MAJOR.value)
        raise ValueError("Neo-Riemannian operations apply to major/minor triads.")

    @staticmethod
    def L(chord: Chord) -> Chord:
        """Leittonwechsel (Leading-tone exchange): Maps major chord to its mediant minor,
        and minor chord to its submediant major.
        C Maj (C-E-G) -> E Min (E-G-B) (Root moves down a semitone)
        C Min (C-Eb-G) -> Ab Maj (Ab-C-Eb) (Fifth moves up a semitone)

        Args:
        ----
            chord (Chord): The chord argument.

        Returns:
        -------
            Chord: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for L

        """
        """Leittonwechsel (Leading-tone exchange): Maps major chord to its mediant minor,
        and minor chord to its submediant major.
        C Maj (C-E-G) -> E Min (E-G-B) (Root moves down a semitone)
        C Min (C-Eb-G) -> Ab Maj (Ab-C-Eb) (Fifth moves up a semitone)"""
        if chord.is_major():
            new_root = (chord.root + 4) % 12  # Up a major third
            return Chord(new_root, ChordType.MINOR.value)
        if chord.is_minor():
            new_root = (chord.root + 8) % 12  # Down a major third
            return Chord(new_root, ChordType.MAJOR.value)
        raise ValueError("L operation requires Major/Minor triad.")

    @staticmethod
    def R(chord: Chord) -> Chord:
        """Relative: Maps a major chord to its relative minor, and vice versa.
        C Maj -> A Min (Fifth moves up a tone)
        C Min -> Eb Maj (Root moves down a tone)

        Args:
        ----
            chord (Chord): The chord argument.

        Returns:
        -------
            Chord: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for R

        """
        """Relative: Maps a major chord to its relative minor, and vice versa.
        C Maj -> A Min (Fifth moves up a tone)
        C Min -> Eb Maj (Root moves down a tone)"""
        if chord.is_major():
            new_root = (chord.root + 9) % 12  # Up a major sixth
            return Chord(new_root, ChordType.MINOR.value)
        if chord.is_minor():
            new_root = (chord.root + 3) % 12  # Up a minor third
            return Chord(new_root, ChordType.MAJOR.value)
        raise ValueError("R operation requires Major/Minor triad.")

    @staticmethod
    def N(chord: Chord) -> Chord:
        """Nebenverwandt: Maps a major chord to its minor subdominant, and minor to major dominant.
        Equivalent to R L P operations chained.

        Args:
        ----
            chord (Chord): The chord argument.

        Returns:
        -------
            Chord: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for N

        """
        """Nebenverwandt: Maps a major chord to its minor subdominant, and minor to major dominant.
        Equivalent to R L P operations chained."""
        return NeoRiemannian.P(NeoRiemannian.L(NeoRiemannian.R(chord)))


# --------------------------------------------------------------------------- #
# 5. Roman Numeral Analysis & Harmony
# --------------------------------------------------------------------------- #


class RomanNumeralAnalysis:
    """Algorithmic mapping between Roman Numerals and chords in a given key.
    Follows common-practice functionality.
    """

    # Mapping of major key degrees built on Ionian: (Interval from root, Chord Type)
    MAJOR_KEY_TRIADS = {
        "I": (0, ChordType.MAJOR),
        "ii": (2, ChordType.MINOR),
        "iii": (4, ChordType.MINOR),
        "IV": (5, ChordType.MAJOR),
        "V": (7, ChordType.MAJOR),
        "vi": (9, ChordType.MINOR),
        "vii°": (11, ChordType.DIMINISHED),
        # Seventh chords
        "Imaj7": (0, ChordType.MAJOR_SEVENTH),
        "ii7": (2, ChordType.MINOR_SEVENTH),
        "V7": (7, ChordType.DOMINANT_SEVENTH),
        # Secondary Dominants
        "V/V": (2, ChordType.MAJOR),
        "V7/V": (2, ChordType.DOMINANT_SEVENTH),
        "V/ii": (9, ChordType.MAJOR),
        "V/vi": (4, ChordType.MAJOR),
    }

    # Minor key degrees (blending natural and harmonic minor context)
    MINOR_KEY_TRIADS = {
        "i": (0, ChordType.MINOR),
        "ii°": (2, ChordType.DIMINISHED),
        "III": (3, ChordType.MAJOR),
        "iv": (5, ChordType.MINOR),
        "v": (7, ChordType.MINOR),
        "V": (7, ChordType.MAJOR),  # Harmonic minor dominant
        "VI": (8, ChordType.MAJOR),
        "VII": (10, ChordType.MAJOR),
        "vii°": (11, ChordType.DIMINISHED),  # Harmonic minor leading-tone
    }

    @classmethod
    def get_chord(cls, numeral: str, key_root: int, is_major_key: bool = True) -> Chord:
        """Function get_chord.

        Args:
        ----
            numeral (str): The numeral argument.
            key_root (int): The key_root argument.
            is_major_key (bool): The is_major_key argument.

        Returns:
        -------
            Chord: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for get_chord

        """
        mapping = cls.MAJOR_KEY_TRIADS if is_major_key else cls.MINOR_KEY_TRIADS
        if numeral not in mapping:
            raise ValueError(f"Unknown roman numeral: {numeral}")

        interval, ctype = mapping[numeral]
        root_pitch = (key_root + interval) % 12
        return Chord(root_pitch, ctype.value)


# --------------------------------------------------------------------------- #
# 6. Counterpoint and Voice Leading
# --------------------------------------------------------------------------- #


class VoiceLeading:
    """Algorithms validating common-practice voice leading rules (Fuxian species counterpoint)."""

    @staticmethod
    def has_parallel_fifths(chord1_notes: list[Note], chord2_notes: list[Note]) -> bool:
        """Check for consecutive perfect fifths between any two voices.

        Args:
        ----
            chord1_notes (Any): The chord1_notes argument.
            chord2_notes (Any): The chord2_notes argument.

        Returns:
        -------
            bool: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for has_parallel_fifths

        """
        """Check for consecutive perfect fifths between any two voices."""
        if len(chord1_notes) != len(chord2_notes):
            return False

        for i in range(len(chord1_notes)):
            for j in range(i + 1, len(chord1_notes)):
                i1 = chord1_notes[j].midi_number - chord1_notes[i].midi_number
                i2 = chord2_notes[j].midi_number - chord2_notes[i].midi_number

                # Perfect fifth is 7 semitones
                if i1 % 12 == 7 and i2 % 12 == 7:
                    # check if the voices actually moved
                    if chord1_notes[j].midi_number != chord2_notes[j].midi_number:
                        return True
        return False

    @staticmethod
    def has_parallel_octaves(
        chord1_notes: list[Note],
        chord2_notes: list[Note],
    ) -> bool:
        """Check for consecutive perfect octaves between any two voices.

        Args:
        ----
            chord1_notes (Any): The chord1_notes argument.
            chord2_notes (Any): The chord2_notes argument.

        Returns:
        -------
            bool: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for has_parallel_octaves

        """
        """Check for consecutive perfect octaves between any two voices."""
        if len(chord1_notes) != len(chord2_notes):
            return False

        for i in range(len(chord1_notes)):
            for j in range(i + 1, len(chord1_notes)):
                i1 = chord1_notes[j].midi_number - chord1_notes[i].midi_number
                i2 = chord2_notes[j].midi_number - chord2_notes[i].midi_number
                if i1 % 12 == 0 and i2 % 12 == 0:
                    if chord1_notes[j].midi_number != chord2_notes[j].midi_number:
                        return True
        return False

    @staticmethod
    def is_independent_motion(
        note1_v1: Note,
        note1_v2: Note,
        note2_v1: Note,
        note2_v2: Note,
    ) -> bool:
        """Determines if two moving voices show independence (contrary or oblique motion)
        as opposed to parallel or similar motion.

        Args:
        ----
            note1_v1 (Note): The note1_v1 argument.
            note1_v2 (Note): The note1_v2 argument.
            note2_v1 (Note): The note2_v1 argument.
            note2_v2 (Note): The note2_v2 argument.

        Returns:
        -------
            bool: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for is_independent_motion

        """
        """
        Determines if two moving voices show independence (contrary or oblique motion)
        as opposed to parallel or similar motion.
        """
        diff1 = note2_v1.midi_number - note1_v1.midi_number
        diff2 = note2_v2.midi_number - note1_v2.midi_number

        # Contrary motion: moving in opposite directions
        if (diff1 > 0 and diff2 < 0) or (diff1 < 0 and diff2 > 0):
            return True

        # Oblique motion: one voice stationary, the other moving
        if (diff1 == 0 and diff2 != 0) or (diff1 != 0 and diff2 == 0):
            return True

        return False


# --------------------------------------------------------------------------- #
# 7. Cadences and Progressions
# --------------------------------------------------------------------------- #


class Cadences:
    """Evaluates progressions for standard cadential patterns."""

    @staticmethod
    def identify(chord1: Chord, chord2: Chord, key_root: int) -> str:
        """Identify cadence type given the last two chords of a phrase.

        Args:
        ----
            chord1 (Chord): The chord1 argument.
            chord2 (Chord): The chord2 argument.
            key_root (int): The key_root argument.

        Returns:
        -------
            str: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for identify

        """
        """Identify cadence type given the last two chords of a phrase."""
        root1_rel = (chord1.root - key_root) % 12
        root2_rel = (chord2.root - key_root) % 12

        is_V_1 = root1_rel == 7 and chord1.is_major()
        is_I_2 = root2_rel == 0 and chord2.is_major()
        is_IV_1 = root1_rel == 5
        is_vi_2 = root2_rel == 9 and chord2.is_minor()

        if is_V_1 and is_I_2:
            return "Authentic Cadence"
        if is_IV_1 and is_I_2:
            return "Plagal Cadence"
        if is_V_1 and is_vi_2:
            return "Deceptive Cadence"
        if is_V_1:
            return "Half Cadence"

        return "None"


# --------------------------------------------------------------------------- #
# 8. Figured Bass Realization
# --------------------------------------------------------------------------- #


class FiguredBass:
    """Translates figured bass symbols into chords.
    Numerals represent intervals above the bass note.
    """

    # Keys map to intervals stacked over the bass.
    FIGURES = {
        "5/3": [0, 4, 7],  # Root position Major
        "6/3": [
            0,
            3,
            8,
        ],  # 1st inversion (minor third, minor sixth over bass -> Major chord rooted on 6th)
        "6/4": [0, 5, 9],  # 2nd inversion
        "7": [0, 4, 7, 10],  # Root position dominant 7th
        "6/5": [0, 3, 6, 9],  # First inversion 7th
        "4/3": [0, 3, 5, 8],  # Second inversion 7th
        "4/2": [0, 2, 5, 9],  # Third inversion 7th
    }

    @staticmethod
    def realize_intervals(figure: str) -> list[int]:
        """Returns the semitone intervals above bass for standard figured types.

        Args:
        ----
            figure (str): The figure argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for realize_intervals

        """
        """Returns the semitone intervals above bass for standard figured types."""
        return FiguredBass.FIGURES.get(figure, [0, 4, 7])


# --------------------------------------------------------------------------- #
# 9. Song Structure and Form
# --------------------------------------------------------------------------- #


class FormAndStructure:
    """Algorithmic generation and analysis of macro musical structures."""

    @staticmethod
    def generate_form(kind: str = "pop_modern") -> list[str]:
        """Returns a list of sections detailing the macro-structure.

        Args:
        ----
            kind (str): The kind argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for generate_form

        """
        """Returns a list of sections detailing the macro-structure."""
        structures = {
            "pop_modern": [
                "Verse 1",
                "Chorus",
                "Verse 2",
                "Chorus",
                "Bridge",
                "Chorus",
                "Outro",
            ],
            "aaba": ["A1", "A2", "B", "A3"],
            "sonata": ["Exposition", "Development", "Recapitulation", "Coda"],
            "rondo": [
                "Refrain (A)",
                "Episode 1 (B)",
                "Refrain (A)",
                "Episode 2 (C)",
                "Refrain (A)",
            ],
            "blues_12_bar": [
                "I",
                "IV",
                "I",
                "I",
                "IV",
                "IV",
                "I",
                "I",
                "V",
                "IV",
                "I",
                "V",
            ],
            "strophic": ["Verse 1", "Verse 2", "Verse 3", "Verse 4"],
        }
        return structures.get(kind.lower(), structures["pop_modern"])

    @staticmethod
    def typical_chord_progression(section: str) -> list[str]:
        """Returns classic functional harmony progression for a given section.

        Args:
        ----
            section (str): The section argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for typical_chord_progression

        """
        """Returns classic functional harmony progression for a given section."""
        if section.startswith("Verse"):
            # Often sets up the chorus without fully resolving to I strongly yet
            return ["I", "vi", "IV", "V"]
        if section.startswith("Chorus"):
            # Strong hook, typically starts on I, resolves cleanly
            return ["I", "V", "vi", "IV"]
        if section.startswith("Bridge"):
            # Contrast, often starts on a minor chord or predominant
            return ["vi", "IV", "ii", "V"]
        return ["I", "IV", "V", "I"]


# --------------------------------------------------------------------------- #
# 9. Acoustic Mathematics & Tuning Systems (Mathematical Sound Topology)
# --------------------------------------------------------------------------- #
class Acoustics:
    """Mathematical representations of frequency, cents, and temperament."""

    @staticmethod
    def freq_equal_temperament(midi_note: float, a4_freq: float = 440.0) -> float:
        """Calculate frequency using 12-Tone Equal Temperament (12-TET).

        Args:
        ----
            midi_note (float): The midi_note argument.
            a4_freq (float): The a4_freq argument.

        Returns:
        -------
            float: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for freq_equal_temperament

        """
        """Calculate frequency using 12-Tone Equal Temperament (12-TET)."""
        return a4_freq * (math.pow(2, (midi_note - 69) / 12.0))

    @staticmethod
    def cents_difference(freq1: float, freq2: float) -> float:
        """Determine logarithmic cents difference between two frequencies.

        Args:
        ----
            freq1 (float): The freq1 argument.
            freq2 (float): The freq2 argument.

        Returns:
        -------
            float: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for cents_difference

        """
        """Determine logarithmic cents difference between two frequencies."""
        return 1200.0 * math.log2(freq2 / freq1)

    @staticmethod
    def harmonic_series(root_freq: float, overtones: int = 8) -> list[float]:
        """Calculates exact integer multiples of the fundamental frequency.

        Args:
        ----
            root_freq (float): The root_freq argument.
            overtones (int): The overtones argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for harmonic_series

        """
        """Calculates exact integer multiples of the fundamental frequency."""
        return [root_freq * n for n in range(1, overtones + 1)]

    @staticmethod
    def just_intonation_ratio(interval_semitones: int) -> tuple[int, int]:
        """Returns standard Ptolemaic just intonation ratio for diatonic intervals.

        Args:
        ----
            interval_semitones (int): The interval_semitones argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for just_intonation_ratio

        """
        """Returns standard Ptolemaic just intonation ratio for diatonic intervals."""
        ratios = {
            0: (1, 1),
            1: (16, 15),
            2: (9, 8),
            3: (6, 5),
            4: (5, 4),
            5: (4, 3),
            6: (45, 32),
            7: (3, 2),
            8: (8, 5),
            9: (5, 3),
            10: (9, 5),
            11: (15, 8),
            12: (2, 1),
        }
        return ratios.get(interval_semitones % 12, (1, 1))


# --------------------------------------------------------------------------- #
# 10. Abstract Musical Set Theory (Fortean Combinatorics)
# --------------------------------------------------------------------------- #
class PitchClassSet:
    """Mathematical Set Theory applied to musical pitches, calculating properties
    like Normal Form, Prime Form, and Interval-Class Vectors.
    Translates music entirely into geometry and arrays.
    """

    def __init__(self, pitches: list[int]):
        """Function __init__.

        Args:
        ----
            pitches (Any): The pitches argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for __init__

        """
        self.pitches = sorted(list(set(p % 12 for p in pitches)))

    def transpose(self, n: int) -> PitchClassSet:
        """Z_12 modular transposition.

        Args:
        ----
            n (int): The n argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for transpose

        """
        """Z_12 modular transposition."""
        return PitchClassSet([(p + n) % 12 for p in self.pitches])

    def invert(self, axis: int = 0) -> PitchClassSet:
        """Z_12 inversion around a given integer axis.

        Args:
        ----
            axis (int): The axis argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for invert

        """
        """Z_12 inversion around a given integer axis."""
        return PitchClassSet([(axis - p) % 12 for p in self.pitches])

    def interval_vector(self) -> tuple[int, int, int, int, int, int]:
        """Calculates occurrences of interval classes 1 through 6 in the set.

        Args:
        ----
            None

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for interval_vector

        """
        """Calculates occurrences of interval classes 1 through 6 in the set."""
        vector = [0] * 6
        for i, p1 in enumerate(self.pitches):
            for p2 in self.pitches[i + 1 :]:
                dist = abs(p2 - p1)
                ic = 12 - dist if dist > 6 else dist
                if ic > 0:
                    vector[ic - 1] += 1
        return cast("tuple[int, int, int, int, int, int]", tuple(vector))

    def normal_form(self) -> list[int]:
        """Finds the most mathematically compact rotational arrangement of the set.

        Args:
        ----
            None

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for normal_form

        """
        """Finds the most mathematically compact rotational arrangement of the set."""
        if not self.pitches:
            return []
        rotations = [
            self.pitches[i:] + [p + 12 for p in self.pitches[:i]]
            for i in range(len(self.pitches))
        ]
        rotations.sort(key=lambda r: [r[-1] - r[0], r[-2] - r[0]])
        best = rotations[0]
        return [p % 12 for p in best]

    def prime_form(self) -> list[int]:
        """Finds Forte Prime Form (canonical minimal Z_12 representative).

        Args:
        ----
            None

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for prime_form

        """
        """Finds Forte Prime Form (canonical minimal Z_12 representative)."""
        nf = self.normal_form()
        if not nf:
            return []
        inv_nf = self.invert().normal_form()

        # Zero-index both approaches to allow mathematical comparison
        nf_zeroed = [(p - nf[0]) % 12 for p in nf]
        inv_zeroed = [(p - inv_nf[0]) % 12 for p in inv_nf]

        # Lexicographically compare arrays to deterministically pick the prime mathematical structure
        return min(inv_zeroed, nf_zeroed)


# --------------------------------------------------------------------------- #
# 11. Mathematics of Rhythm & Meter Symmetries
# --------------------------------------------------------------------------- #
class MathematicalRhythm:
    """Algorithms defining time grids, polyrhythms, and beat topology."""

    @staticmethod
    def bjorklund_euclidean(pulses: int, steps: int) -> list[int]:
        """Bjorklund's algorithm structurally modeling neutron spallation
        (but it miraculously generates almost all world music rhythms).
        Distributes `pulses` evenly over `steps`.
        E.g., E(3,8) -> Tresillo [1, 0, 0, 1, 0, 0, 1, 0]

        Args:
        ----
            pulses (int): The pulses argument.
            steps (int): The steps argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for bjorklund_euclidean

        """
        """
        Bjorklund's algorithm structurally modeling neutron spallation
        (but it miraculously generates almost all world music rhythms).
        Distributes `pulses` evenly over `steps`.
        E.g., E(3,8) -> Tresillo [1, 0, 0, 1, 0, 0, 1, 0]
        """
        if pulses > steps or pulses <= 0:
            return [0] * steps

        pattern = [[1] for _ in range(pulses)] + [[0] for _ in range(steps - pulses)]
        while len(pattern) > pulses and len(set(tuple(x) for x in pattern)) > 1:
            zeros = [x for x in pattern if x == [0]]
            ones = [x for x in pattern if x != [0]]
            if not zeros:
                break

            for i in range(min(len(ones), len(zeros))):
                ones[i].extend(zeros[i])
            pattern = ones + zeros[len(ones) :]

        return [item for sublist in pattern for item in sublist]

    @staticmethod
    def longuet_higgins_syncopation(binary_rhythm: list[int]) -> float:
        """Calculates mathematical syncopation using a simplified Longuet-Higgins & Lee metric.
        Notes on weak metrical nodes resolving into silence on strong nodes accumulate tension.

        Args:
        ----
            binary_rhythm (Any): The binary_rhythm argument.

        Returns:
        -------
            float: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for longuet_higgins_syncopation

        """
        """
        Calculates mathematical syncopation using a simplified Longuet-Higgins & Lee metric.
        Notes on weak metrical nodes resolving into silence on strong nodes accumulate tension.
        """
        n = len(binary_rhythm)
        if n not in (8, 16):
            return 0.0  # Only handles standard rigid grids for now

        weights = (
            [0, -3, -2, -3, -1, -3, -2, -3]
            if n == 8
            else [0, -4, -3, -4, -2, -4, -3, -4, -1, -4, -3, -4, -2, -4, -3, -4]
        )

        score = 0
        for i in range(n):
            if binary_rhythm[i] == 1:
                next_pos = (i + 1) % n
                if binary_rhythm[next_pos] == 0 and weights[next_pos] > weights[i]:
                    score += weights[next_pos] - weights[i]
        return float(score)



# --------------------------------------------------------------------------- #
# 12. Negative Harmony (Polarity Symmetries)
# --------------------------------------------------------------------------- #
class NegativeHarmony:
    """Music polarity mirroring mapping notes across a dual-root axis.
    Treats traditional tonality as one hemisphere of an invertible geometry.
    """

    @staticmethod
    def invert_pitch(
        pitch_class: int,
        axis_root1: int,
        axis_root2: int,
    ) -> int:
        """Reflects a single pitch class around the exact midpoint of two axis notes.
        Usually axis is the root and dominant fifth (e.g., C and G -> midpoint E/Eb).

        Args:
        ----
            pitch_class (int): The pitch_class argument.
            axis_root1 (int): The axis_root1 argument.
            axis_root2 (int): The axis_root2 argument.

        Returns:
        -------
            int: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for invert_pitch

        """
        """
        Reflects a single pitch class around the exact midpoint of two axis notes.
        Usually axis is the root and dominant fifth (e.g., C and G -> midpoint E/Eb).
        """
        axis_sum = (axis_root1 + axis_root2) % 12
        return (axis_sum - pitch_class) % 12

    @staticmethod
    def mirror_chord(
        chord_pitches: list[int],
        axis_root1: int,
        axis_root2: int,
    ) -> list[int]:
        """Inverts a list of pitches. Converts major harmony into minor, and
        dominant 7th chords into half-diminished/minor-6th geometries.

        Args:
        ----
            chord_pitches (Any): The chord_pitches argument.
            axis_root1 (int): The axis_root1 argument.
            axis_root2 (int): The axis_root2 argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for mirror_chord

        """
        """
        Inverts a list of pitches. Converts major harmony into minor, and
        dominant 7th chords into half-diminished/minor-6th geometries.
        """
        return sorted([(axis_root1 + axis_root2 - p) % 12 for p in chord_pitches])



# --------------------------------------------------------------------------- #
# 13. Advanced Topologies & Voice Leading Vectorization
# --------------------------------------------------------------------------- #
class TopologicalVoiceLeading:
    """Calculates multidimensional paths through chord-spaces."""

    @staticmethod
    def minimal_work_metric(
        chord1_pitches: list[int],
        chord2_pitches: list[int],
    ) -> int:
        """Uses combinatorial permutation to find the absolute minimal total
        semitonal distance required to morph chord 1 into chord 2.
        Operates exactly like the 'taxicab block distance' in mathematics.

        Args:
        ----
            chord1_pitches (Any): The chord1_pitches argument.
            chord2_pitches (Any): The chord2_pitches argument.

        Returns:
        -------
            int: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for minimal_work_metric

        """
        """
        Uses combinatorial permutation to find the absolute minimal total
        semitonal distance required to morph chord 1 into chord 2.
        Operates exactly like the 'taxicab block distance' in mathematics.
        """
        if len(chord1_pitches) != len(chord2_pitches):
            raise ValueError("Arrays must be symmetrical for vector work metrics.")

        c1 = sorted(p % 12 for p in chord1_pitches)
        c2 = [p % 12 for p in chord2_pitches]

        min_work = float("inf")
        for perm in itertools.permutations(c2):
            work = sum(min(abs(a - b), 12 - abs(a - b)) for a, b in zip(c1, perm))
            min_work = min(min_work, work)

        if min_work == float("inf"):
            return 0
        return int(min_work)


# --------------------------------------------------------------------------- #
# 14. Algorithmic Stochastic Generation
# --------------------------------------------------------------------------- #
class MarkovGenerativeHarmony:
    """Stochastic matrices mapping chord probabilities. Removes human impulse, replaces with statistically weighted architectural flows."""

    # Common Practice Transition Matrix Network (Row = Current State, Weights = Prob of Next State)
    MATRICES: dict[str, dict[str, dict[str, float]]] = {
        "MAJOR_DIATONIC": {
            "I": {
                "I": 0.05,
                "ii": 0.15,
                "iii": 0.05,
                "IV": 0.25,
                "V": 0.30,
                "vi": 0.15,
                "vii°": 0.05,
            },
            "ii": {"V": 0.60, "vii°": 0.20, "ii": 0.05, "vi": 0.15},
            "iii": {"vi": 0.60, "IV": 0.30, "iii": 0.10},
            "IV": {"V": 0.40, "I": 0.30, "ii": 0.20, "vii°": 0.10},
            "V": {
                "I": 0.70,
                "vi": 0.20,
                "V": 0.10,
            },  # Dominant resolves authentic or deceptive
            "vi": {"IV": 0.40, "ii": 0.40, "V": 0.15, "iii": 0.05},
            "vii°": {"I": 0.80, "vi": 0.20},
        },
    }

    @staticmethod
    def highly_probable_path(start_node: str, depth: int) -> list[str]:
        """Calculates a strictly deterministic path of highest mathematical probability.

        Args:
        ----
            start_node (str): The start_node argument.
            depth (int): The depth argument.

        Returns:
        -------
            list[str]: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for highly_probable_path

        """
        """Calculates a strictly deterministic path of highest mathematical probability."""
        path: list[str] = [start_node]
        current = start_node
        matrix = MarkovGenerativeHarmony.MATRICES["MAJOR_DIATONIC"]

        for _ in range(depth - 1):
            transitions = matrix.get(current, {"I": 1.0})
            best_next = max(transitions.items(), key=lambda k: k[1])[0]
            path.append(best_next)
            current = best_next

        return path

# --------------------------------------------------------------------------- #
# 15. Serialism & 12-Tone Combinatorial Matrix (Schoenberg Topology)
# --------------------------------------------------------------------------- #
class SerialMatrix:
    """Constructs a 12x12 mathematical matrix indexing all possible transformations
    (Prime, Inversion, Retrograde, Retrograde-Inversion) of a dodecaphonic row.
    Music is reduced to an absolute permutation grid.
    """

    def __init__(self, prime_row: list[int]):
        """Initializes with a 12-tone row (array of 12 unique integers 0-11).

        Args:
        ----
            prime_row (Any): The prime_row argument.

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for __init__

        """
        """Initializes with a 12-tone row (array of 12 unique integers 0-11)."""
        if len(set(p % 12 for p in prime_row)) != 12:
            raise ValueError(
                "A strict serial matrix requires exactly 12 unique pitch classes.",
            )
        self.prime_0 = [p % 12 for p in prime_row]
        self.matrix: list[list[int]] = self._generate_matrix()

    def _generate_matrix(self) -> list[list[int]]:
        """Calculates the grid:
        Row 0 is Prime (P0).
        Col 0 is Inversion (I0).
        Matrix[i][j] = (I0[i] + P0[j] - P0[0]) mod 12

        Args:
        ----
            None

        Returns:
        -------
            None: The return value.

        Processing Logic:
        -------------------
            - Executes the logic for _generate_matrix

        """
        """
        Calculates the grid:
        Row 0 is Prime (P0).
        Col 0 is Inversion (I0).
        Matrix[i][j] = (I0[i] + P0[j] - P0[0]) mod 12
        """
        p_zero = self.prime_0
        first_note = p_zero[0]
        i_zero = [(first_note - (p - first_note)) % 12 for p in p_zero]

        matrix = []
        for i_note in i_zero:
            transposition = (i_note - first_note) % 12
            row = [(p + transposition) % 12 for p in p_zero]
            matrix.append(row)

        return matrix

    def get_prime(self, offset: int = 0) -> list[int]:
        """Function get_prime.

        Args:
        ----
            offset (int): The offset argument.

        Returns:
        -------
            list[int]: The prime row with the specified offset.

        Processing Logic:
        -------------------
            - Executes the logic for get_prime

        """
        target_start = (self.matrix[0][0] + offset) % 12
        for row in self.matrix:
            if row[0] == target_start:
                return row
        return self.matrix[0]

    def get_retrograde(self, offset: int = 0) -> list[int]:
        """Function get_retrograde.

        Args:
        ----
            offset (int): The offset argument.

        Returns:
        -------
            list[int]: The retrograde row with the specified offset.

        Processing Logic:
        -------------------
            - Executes the logic for get_retrograde

        """
        return list(reversed(self.get_prime(offset)))

    def get_inversion(self, offset: int = 0) -> list[int]:
        """Function get_inversion.

        Args:
        ----
            offset (int): The offset argument.

        Returns:
        -------
            list[int]: The inversion row with the specified offset.

        Processing Logic:
        -------------------
            - Executes the logic for get_inversion

        """
        target_start = (self.matrix[0][0] + offset) % 12
        for col_idx in range(12):
            if self.matrix[0][col_idx] == target_start:
                return [self.matrix[row_idx][col_idx] for row_idx in range(12)]
        return [self.matrix[row_idx][0] for row_idx in range(12)]

    def get_retrograde_inversion(self, offset: int = 0) -> list[int]:
        """Function get_retrograde_inversion.

        Args:
        ----
            offset (int): The offset argument.

        Returns:
        -------
            list[int]: The retrograde inversion row with the specified offset.

        Processing Logic:
        -------------------
            - Executes the logic for get_retrograde_inversion

        """
        return list(reversed(self.get_inversion(offset)))


# --------------------------------------------------------------------------- #
# 16. Fourier-Transforms of Pitch Profiles (DFT Pitch-Class Space)
# --------------------------------------------------------------------------- #


class PitchClassFourier:
    """Applies Discrete Fourier Transform (DFT) to 12-tone pitch-class distributions
    to mathematically extract the hidden 'symmetries' and 'brightness' vectors
    of a chord or scale without any human heuristic.
    """

    @staticmethod
    def calculate_dft(pc_vector: list[float]) -> list[complex]:
        """Takes a 12-element array (weights of each pitch class C to B)
        and returns its 12 complex Fourier coefficients.

        Args:
        ----
            pc_vector (list[float]): The pc_vector argument.

        Returns:
        -------
            list[complex]: The 12 complex Fourier coefficients.

        Processing Logic:
        -------------------
            - Executes the logic for calculate_dft

        """
        """
        Takes a 12-element array (weights of each pitch class C to B)
        and returns its 12 complex Fourier coefficients.
        """
        if len(pc_vector) != 12:
            raise ValueError("DFT requires exactly 12 pitch classes or weights.")

        coefficients = []
        for k in range(12):
            f_k = sum(
                pc_vector[n] * cmath.exp(-2j * math.pi * k * n / 12) for n in range(12)
            )
            coefficients.append(f_k)

        return coefficients

    @staticmethod
    def diatonic_magnitude(pc_vector: list[float]) -> float:
        """Mathematically quantifies "how Diatonic" a set of notes is
        by calculating the magnitude of the 5th Fourier coefficient.

        Args:
        ----
            pc_vector (list[float]): The pc_vector argument.

        Returns:
        -------
            float: The magnitude of the 5th Fourier coefficient.

        Processing Logic:
        -------------------
            - Executes the logic for diatonic_magnitude

        """
        """
        Mathematically quantifies "how Diatonic" a set of notes is
        by calculating the magnitude of the 5th Fourier coefficient.
        """
        dft = PitchClassFourier.calculate_dft(pc_vector)
        return abs(dft[5])
