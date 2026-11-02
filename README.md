# Deutsch Anki Builder

A small Python project that turns a German–Persian vocabulary CSV into an Anki `.apkg` deck with German word audio and optional example audio.

## Project structure

```text
Deutsch_Anki_Builder/
├── data/
│   └── my_vocab.csv
├── audio/                 # generated MP3 files (not committed)
├── output/                # generated APKG file (not committed)
├── build_deck.py
├── requirements.txt
└── README.md
```

## CSV columns

The CSV must contain these exact headers:

`German,Type,Article,Plural,Persian,Example,Example Persian,Tags`

- `Type`: use values such as `noun`, `verb`, `adjective`, `adverb`, `expression`.
- `Article`: `der`, `die`, or `das` for nouns; leave blank otherwise.
- `Plural`: plural form for nouns; leave blank if unknown/not applicable.
- `Tags`: level such as `A1`, `A2`, `B1`. Multiple tags can be separated with semicolons.
- `Example` and `Example Persian` are optional. If an example is present, the script also tries to create its audio.

## Setup (Windows PowerShell)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Build the deck

```powershell
python build_deck.py
```

The script reads `data/my_vocab.csv` and creates:

`output/German_Vocabulary.apkg`

Import that APKG into Anki. Each vocabulary item creates two cards:
1. German → Persian
2. Persian → German

Audio generation uses Microsoft Edge TTS and therefore requires an internet connection for any audio file that is not already cached in `audio/`. The generated MP3 files are embedded in the APKG.

## Notes

- Repeated headwords are retained when their meaning, examples, or level differ. Only completely identical rows are skipped.
- Existing audio files are reused.
- Missing examples do not prevent deck creation.
- The card styling is intentionally simple; visual design can be upgraded later.
