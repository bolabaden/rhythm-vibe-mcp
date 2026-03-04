"""Scale patterns and mode generation."""

__all__ = [
    "Scales",
]

class Scales:
    """Scale patterns defined by semitone offsets from the root."""

    MAJOR = [0, 2, 4, 5, 7, 9, 11]
    NATURAL_MINOR = [0, 2, 3, 5, 7, 8, 10]
    HARMONIC_MINOR = [0, 2, 3, 5, 7, 8, 11]
    MELODIC_MINOR = [0, 2, 3, 5, 7, 9, 11]

    IONIAN = MAJOR
    DORIAN = [0, 2, 3, 5, 7, 9, 10]
    PHRYGIAN = [0, 1, 3, 5, 7, 8, 10]
    LYDIAN = [0, 2, 4, 6, 7, 9, 11]
    MIXOLYDIAN = [0, 2, 4, 5, 7, 9, 10]
    AEOLIAN = NATURAL_MINOR
    LOCRIAN = [0, 1, 3, 5, 6, 8, 10]

    MAJOR_PENTATONIC = [0, 2, 4, 7, 9]
    MINOR_PENTATONIC = [0, 3, 5, 7, 10]
    BLUES = [0, 3, 5, 6, 7, 10]
    WHOLE_TONE = [0, 2, 4, 6, 8, 10]
    OCTATONIC_HW = [0, 1, 3, 4, 6, 7, 9, 10]

    @staticmethod
    def generate_scale(root_pitch: int, pattern: list[int]) -> list[int]:
        return [(root_pitch + interval) % 12 for interval in pattern]
