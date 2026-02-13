"""LilyPond notation constants: key signatures, time signatures, tempo marks."""

# Version string for \\version in generated .ly files
LILYPOND_VERSION = "2.24.0"

# Default clef when instrument is not in the clef map (bass-clef instruments by default)
DEFAULT_CLEF = "bass"

# Default key/time/tempo when name not in maps (used by lilypond_key, lilypond_time_sig, lilypond_tempo)
LILYPOND_DEFAULT_KEY = "e \\minor"
LILYPOND_DEFAULT_TIME = "3/4"
LILYPOND_DEFAULT_TEMPO = "Lento e cantabile"

# File extension for LilyPond source files
LILYPOND_EXTENSION = ".ly"

# Comment prefix for prompt seed in generated .ly (traceability)
LILYPOND_PROMPT_SEED_COMMENT = "% Prompt seed (truncated for traceability):"

# Key signature: display name -> LilyPond \\key syntax
LILYPOND_KEYS: dict[str, str] = {
    "c": "c \\major",
    "cmaj": "c \\major",
    "c major": "c \\major",
    "cm": "c \\minor",
    "c min": "c \\minor",
    "c minor": "c \\minor",
    "c#": "cis \\major",
    "c# major": "cis \\major",
    "c#m": "cis \\minor",
    "c# minor": "cis \\minor",
    "db": "des \\major",
    "d flat": "des \\major",
    "d flat major": "des \\major",
    "dbm": "des \\minor",
    "d": "d \\major",
    "d major": "d \\major",
    "dm": "d \\minor",
    "d minor": "d \\minor",
    "d#": "dis \\major",
    "d#m": "dis \\minor",
    "eb": "es \\major",
    "e flat": "es \\major",
    "ebm": "es \\minor",
    "e": "e \\major",
    "e major": "e \\major",
    "em": "e \\minor",
    "e minor": "e \\minor",
    "f": "f \\major",
    "f major": "f \\major",
    "fm": "f \\minor",
    "f minor": "f \\minor",
    "f#": "fis \\major",
    "f# major": "fis \\major",
    "f#m": "fis \\minor",
    "f# minor": "fis \\minor",
    "gb": "ges \\major",
    "g flat": "ges \\major",
    "gbm": "ges \\minor",
    "g": "g \\major",
    "g major": "g \\major",
    "gm": "g \\minor",
    "g minor": "g \\minor",
    "g#": "gis \\major",
    "g#m": "gis \\minor",
    "ab": "aes \\major",
    "a flat": "aes \\major",
    "abm": "aes \\minor",
    "a": "a \\major",
    "a major": "a \\major",
    "am": "a \\minor",
    "a minor": "a \\minor",
    "a#": "ais \\major",
    "a#m": "ais \\minor",
    "bb": "bes \\major",
    "b flat": "bes \\major",
    "bbm": "bes \\minor",
    "b": "b \\major",
    "b major": "b \\major",
    "bm": "b \\minor",
    "b minor": "b \\minor",
}

# Time signature: name -> LilyPond \\time
LILYPOND_TIME_SIGS: dict[str, str] = {
    "2/2": "2/2",
    "2/4": "2/4",
    "3/4": "3/4",
    "4/4": "4/4",
    "3/8": "3/8",
    "6/8": "6/8",
    "9/8": "9/8",
    "12/8": "12/8",
    "5/4": "5/4",
    "7/8": "7/8",
    "5/8": "5/8",
    "c": "4/4",
    "c|": "2/2",
}

# Tempo marks: name -> LilyPond \\tempo string
LILYPOND_TEMPO_MARKS: dict[str, str] = {
    "grave": "Grave",
    "largo": "Largo",
    "larghetto": "Larghetto",
    "adagio": "Adagio",
    "adagietto": "Adagietto",
    "lento": "Lento",
    "lentamente": "Lentamente",
    "andante": "Andante",
    "andantino": "Andantino",
    "moderato": "Moderato",
    "allegretto": "Allegretto",
    "allegro": "Allegro",
    "vivace": "Vivace",
    "presto": "Presto",
    "prestissimo": "Prestissimo",
    "lento e cantabile": "Lento e cantabile",
    "andante con moto": "Andante con moto",
    "adagio sostenuto": "Adagio sostenuto",
    "allegro ma non troppo": "Allegro ma non troppo",
    "largo e mesto": "Largo e mesto",
}


def lilypond_key(key_name: str) -> str:
    """Return LilyPond \\key syntax for the given key name."""
    k = key_name.lower().strip()
    return LILYPOND_KEYS.get(k, LILYPOND_DEFAULT_KEY)


def lilypond_time_sig(sig: str) -> str:
    """Return LilyPond \\time value."""
    s = sig.strip()
    return LILYPOND_TIME_SIGS.get(s, LILYPOND_DEFAULT_TIME)


def lilypond_tempo(tempo_name: str) -> str:
    """Return LilyPond tempo mark."""
    t = tempo_name.lower().strip()
    return LILYPOND_TEMPO_MARKS.get(t, LILYPOND_DEFAULT_TEMPO)
