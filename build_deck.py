import asyncio
import csv
import hashlib
import re
from pathlib import Path

import edge_tts
import genanki

ROOT = Path(__file__).resolve().parent
CSV_FILE = ROOT / "data" / "my_vocab.csv"
AUDIO_DIR = ROOT / "audio"
OUTPUT_DIR = ROOT / "output"

VOICE = "de-DE-KatjaNeural"
DECK_NAME = "German Vocabulary"
MODEL_ID = 1607392320
DECK_ID = 2059400110

REQUIRED_FIELDS = [
    "German", "Type", "Article", "Plural", "Persian",
    "Example", "Example Persian", "Tags"
]

MODEL = genanki.Model(
    MODEL_ID,
    "German Vocabulary - Audio",
    fields=[
        {"name": "PureWord"},
        {"name": "FullWord"},
        {"name": "Plural"},
        {"name": "Meaning"},
        {"name": "Example_DE"},
        {"name": "Example_FA"},
        {"name": "Grammar"},
        {"name": "Tags"},
        {"name": "WordAudio"},
        {"name": "ExampleAudio"},
    ],
    templates=[
        {
            "name": "German to Persian",
            "qfmt": """
                <div class="level">{{Tags}}</div>
                <div class="word">{{FullWord}}</div>
                {{#WordAudio}}<div class="audio">{{WordAudio}}</div>{{/WordAudio}}
            """,
            "afmt": """
                {{FrontSide}}<hr id="answer">
                <div class="meaning">{{Meaning}}</div>
                {{#Plural}}<div class="detail"><b>Plural:</b> {{Plural}}</div>{{/Plural}}
                {{#Example_DE}}<div class="example">{{Example_DE}}</div>{{/Example_DE}}
                {{#Example_FA}}<div class="translation">{{Example_FA}}</div>{{/Example_FA}}
                {{#ExampleAudio}}<div class="audio">{{ExampleAudio}}</div>{{/ExampleAudio}}
                <div class="type">{{Grammar}}</div>
            """,
        },
        {
            "name": "Persian to German",
            "qfmt": """
                <div class="level">{{Tags}}</div>
                <div class="meaning">{{Meaning}}</div>
            """,
            "afmt": """
                {{FrontSide}}<hr id="answer">
                <div class="word">{{FullWord}}</div>
                {{#WordAudio}}<div class="audio">{{WordAudio}}</div>{{/WordAudio}}
                {{#Plural}}<div class="detail"><b>Plural:</b> {{Plural}}</div>{{/Plural}}
                {{#Example_DE}}<div class="example">{{Example_DE}}</div>{{/Example_DE}}
                {{#Example_FA}}<div class="translation">{{Example_FA}}</div>{{/Example_FA}}
                {{#ExampleAudio}}<div class="audio">{{ExampleAudio}}</div>{{/ExampleAudio}}
                <div class="type">{{Grammar}}</div>
            """,
        },
    ],
    css="""
.card { font-family: Arial, sans-serif; font-size: 22px; text-align: center;
        background: #f4f6f8; color: #20242a; padding: 24px; }
.level { color: #657080; font-size: 12px; letter-spacing: 1px; margin-bottom: 24px; }
.word { font-size: 34px; font-weight: 700; line-height: 1.4; margin: 28px 0; }
.meaning { font-size: 26px; direction: rtl; line-height: 1.7; margin: 24px 0; }
.detail { margin: 18px 0; color: #465466; }
.example { margin-top: 22px; font-size: 21px; }
.translation { direction: rtl; margin-top: 8px; color: #596575; }
.type { margin-top: 22px; color: #8993a0; font-size: 12px; }
.audio { margin: 14px 0; }
.nightMode .card { background: #202329; color: #f1f3f5; }
""",
)

def clean_filename(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9äöüß]+", "_", value)
    return value.strip("_")[:45] or "audio"

def guid_for(value: str) -> int:
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(digest[:15], 16)

def normalize_tags(value: str) -> list[str]:
    tags = [re.sub(r"\s+", "_", item.strip()) for item in (value or "").split(";")]
    tags = [tag for tag in tags if tag]
    return tags or ["Unsorted"]

def full_word(german: str, word_type: str, article: str) -> str:
    if (word_type or "").strip().lower() == "noun" and article:
        if not re.match(r"^(der|die|das)\s+", german.strip(), flags=re.I):
            return f"{article} {german}"
    return german

async def make_audio(text: str, prefix: str, media: list[str]) -> str:
    text = (text or "").strip()
    if not text or text in {"-", "—"}:
        return ""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{clean_filename(text)}.mp3"
    path = AUDIO_DIR / filename
    if not path.exists():
        try:
            await edge_tts.Communicate(text, VOICE).save(str(path))
            print(f"[audio] created: {text}")
        except Exception as exc:
            print(f"[audio warning] {text}: {exc}")
            return ""
    media.append(str(path))
    return f"[sound:{filename}]"

async def main():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [field for field in REQUIRED_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CSV header missing columns: {missing}")

        deck = genanki.Deck(DECK_ID, DECK_NAME)
        media_files = []
        seen_rows = set()
        count = 0

        for row_number, row in enumerate(reader, start=2):
            german = (row.get("German") or "").strip()
            if not german:
                print(f"[skip] row {row_number}: empty German field")
                continue

            word_type = (row.get("Type") or "").strip().lower()
            article = (row.get("Article") or "").strip()
            plural = (row.get("Plural") or "").strip()
            persian = (row.get("Persian") or "").strip()
            example_de = (row.get("Example") or "").strip()
            example_fa = (row.get("Example Persian") or "").strip()
            tags = normalize_tags(row.get("Tags") or "")

            # Keep the same headword when it has a different meaning/level.
            # Skip only completely identical vocabulary records.
            row_key = "\\x1f".join([
                german.casefold(), word_type, article, plural, persian,
                example_de, example_fa, ";".join(tags)
            ])
            if row_key in seen_rows:
                print(f"[exact duplicate] row {row_number}: {german}")
                continue
            seen_rows.add(row_key)

            complete_word = full_word(german, word_type, article)
            word_audio = await make_audio(complete_word, "word", media_files)
            example_audio = await make_audio(example_de, "example", media_files)

            note = genanki.Note(
                model=MODEL,
                fields=[
                    german, complete_word, plural, persian,
                    example_de, example_fa, word_type.upper(),
                    ", ".join(tags), word_audio, example_audio
                ],
                guid=guid_for(row_key),
                tags=tags,
            )
            deck.add_note(note)
            count += 1
            print(f"[note] {count}: {complete_word}")

    output = OUTPUT_DIR / "German_Vocabulary.apkg"
    package = genanki.Package(deck)
    package.media_files = list(dict.fromkeys(media_files))
    package.write_to_file(str(output))

    print("\n[done] Anki deck created.")
    print(f"[notes] {count}")
    print(f"[cards] {count * 2}")
    print(f"[file] {output}")

if __name__ == "__main__":
    asyncio.run(main())
