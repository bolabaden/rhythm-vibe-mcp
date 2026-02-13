"""Message strings used when building robust fallback from text (ABC, ChordPro, freeform)."""

# ABC
MSG_ABC_PARSED_USE_CONVERT = (
    "ABC notation parsed; use convert_text_notation_to_lily_or_fallback for LilyPond/MusicXML output."
)
MSG_ABC_HEADERS_NO_EVENTS = "ABC headers detected but no note events parsed from body."

# ChordPro
MSG_CHORDPRO_CHORDS_USE_CONVERT = (
    "ChordPro chords extracted; lead-sheet format. Use convert_text_notation for sheet output."
)
MSG_CHORDPRO_NO_CHORDS = "ChordPro-style text detected; no chord symbols extracted."

# Freeform
MSG_FREEFORM_NO_TOKENS = (
    "Freeform text; no pitch or chord tokens extracted. Paste ABC or ChordPro for richer parsing."
)
MSG_FREEFORM_TOKENS_USE_ABC = (
    "Freeform pitch/chord tokens extracted; paste ABC notation for full conversion."
)
