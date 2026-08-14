"""Is there a human voice in this file? (CLAP zero-shot classification)

WHY THIS EXISTS
    Whisper tells you WHAT was said, but it cannot tell you whether anything was
    said at all -- on a blade hum it invents a sentence. And it is blind to
    wordless human sounds: a laugh, a grunt, a scream carry no words, so Whisper
    returns nothing and you cannot tell them apart from a sound effect.

    This matters when separating `force*.wav` (Force effects) from `quote*.wav`
    (spoken lines), because font authors routinely file speech under either name.

WHY A CLASSIFIER RATHER THAN A DESCRIBING MODEL
    A model that GENERATES text can never say "I don't know" -- it says something
    fluent instead, and fluent-but-empty looks exactly like a good answer. A
    large audio-language model tested on this task scored 1 in 16 on non-speech
    files, and when the prompt mentioned lightsabers it simply echoed the prompt
    back for every file.

    CLAP does not write. It scores a fixed list of labels that you supply, so
    "I don't know" shows up honestly as a narrow margin between the top two.

WHAT IT IS AND IS NOT GOOD AT
    Telling voice from sound: reliable.
    Telling one KIND of sound from another (clash vs blaster vs swing): weak --
    in a single sound font those are often built from the same sonic palette.
    Treat the category as a hint and the voice/sound verdict as the answer.

USAGE
    python tools/classify.py --source E:/ --families force,quote
    python tools/classify.py --file "E:/IWVader/quote03.wav"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.sound_library import effect_family, split_font_path  # noqa: E402

MODEL_ID = "laion/larger_clap_general"
SAMPLE_RATE = 48000  # CLAP operates at 48 kHz

# Below this margin the answer is not trusted. Chosen from observation: the
# single binary error on a known-answer test set had a margin of 0.014.
UNCERTAIN_BELOW = 0.05

# CLAP was trained on audio-caption pairs, so full descriptive sentences work
# better than single words. Several phrasings per category average out the
# accident of wording.
VOICE_LABELS = {
    "speech": [
        "a person speaking words in a sentence",
        "a man talking, movie dialogue",
        "a voice pronouncing words",
    ],
    "vocalization": [
        "a person laughing out loud",
        "a wordless human grunt or moan",
        "someone screaming without words",
    ],
}

SOUND_LABELS = {
    "hum": [
        "a continuous steady humming drone that does not stop",
        "a sustained low electrical buzz",
        "a constant looping tone of an energy field",
    ],
    "clash": [
        "two metal blades striking each other, a ringing clang",
        "a hard metallic collision with resonance",
    ],
    "blaster": [
        "a science fiction blaster gun firing a laser bolt",
        "a pew pew laser gun shot",
    ],
    "swing": [
        "a whoosh of an object swinging fast through the air",
        "air rushing as something sweeps past",
    ],
    "music": [
        "orchestral background music with instruments",
        "a musical melody",
    ],
}

ALL_LABELS = {**VOICE_LABELS, **SOUND_LABELS}
FLAT_LABELS = [(category, text)
               for category, texts in ALL_LABELS.items() for text in texts]


def calibrate(matrix):
    """Remove each label's average score across the whole set.

    A label that scores high on everything is an attractor, not a signal.
    Subtracting its mean takes away the advantage it gets for free.
    """
    return matrix - matrix.mean(axis=0, keepdims=True)


def aggregate_by_category(row, categories) -> dict[str, float]:
    """Best-scoring label within each category."""
    best: dict[str, float] = {}
    for category, score in zip(categories, row):
        best[category] = max(best.get(category, float("-inf")), float(score))
    return best


def verdict(per_category: dict[str, float], voice_categories,
            threshold: float = UNCERTAIN_BELOW) -> dict:
    """Decide voice vs sound, and say how sure we are.

    The margin is measured between the best VOICE score and the best SOUND
    score -- not between the top two categories overall. "speech" and
    "vocalization" disagreeing is an argument inside a single answer (a human
    is audible either way), and must not be mistaken for uncertainty.
    """
    best_voice = max(per_category[c] for c in voice_categories if c in per_category)
    best_sound = max(v for k, v in per_category.items() if k not in voice_categories)
    margin = abs(best_voice - best_sound)
    return {
        "voice": best_voice > best_sound,
        "category": max(per_category.items(), key=lambda kv: kv[1])[0],
        "margin": round(margin, 4),
        "confident": margin >= threshold,
        "scores": {k: round(v, 4)
                   for k, v in sorted(per_category.items(), key=lambda kv: -kv[1])},
    }


def _embedding(output):
    """Normalised vector from a CLAP output.

    get_text_features / get_audio_features return a model output object rather
    than a bare tensor. The shared audio-text space lives in `pooler_output`;
    `last_hidden_state` has a different width and is NOT comparable across
    modalities.
    """
    import torch

    tensor = output if isinstance(output, torch.Tensor) else output.pooler_output
    return tensor / tensor.norm(dim=-1, keepdim=True)


class Classifier:
    def __init__(self, model_id: str = MODEL_ID):
        import torch
        from transformers import ClapModel, ClapProcessor

        self._torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = ClapProcessor.from_pretrained(model_id)
        self.model = ClapModel.from_pretrained(model_id).to(self.device).eval()
        self.categories = [c for c, _ in FLAT_LABELS]

        with torch.no_grad():
            inputs = self.processor(text=[t for _, t in FLAT_LABELS],
                                    return_tensors="pt", padding=True).to(self.device)
            self.text_embeddings = _embedding(self.model.get_text_features(**inputs))

    def similarities(self, paths: list[Path]):
        import librosa
        import numpy as np

        rows = []
        for path in paths:
            audio, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
            with self._torch.no_grad():
                inputs = self.processor(audio=audio, sampling_rate=SAMPLE_RATE,
                                        return_tensors="pt").to(self.device)
                embedding = _embedding(self.model.get_audio_features(**inputs))
                rows.append((embedding @ self.text_embeddings.T)
                            .squeeze(0).cpu().numpy())
        return np.stack(rows)

    def classify(self, paths: list[Path]) -> list[dict]:
        """Classify a batch. Calibration needs a batch to work from.

        With fewer than 8 files there is nothing to average against, so
        calibration is skipped and the caller is told.
        """
        raw = self.similarities(paths)
        calibrated = calibrate(raw) if len(paths) >= 8 else raw

        results = []
        for index, path in enumerate(paths):
            per_category = aggregate_by_category(calibrated[index], self.categories)
            outcome = verdict(per_category, set(VOICE_LABELS))
            outcome["file"] = str(path)
            outcome["calibrated"] = len(paths) >= 8
            results.append(outcome)
        return results


def collect(source: Path, families: set[str]) -> list[Path]:
    found = []
    for path in sorted(source.rglob("*.wav")):
        _, relative = split_font_path(path, source)
        if effect_family(relative) in families:
            found.append(path)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Classify sound font files as human voice or sound effect.")
    ap.add_argument("--source", default="", help="card root, e.g. 'E:/'")
    ap.add_argument("--file", default="", help="a single file")
    ap.add_argument("--families", default="force,quote",
                    help="effect families to inspect, comma separated")
    ap.add_argument("--output", default="classification.json")
    args = ap.parse_args()

    if args.file:
        paths = [Path(args.file)]
    elif args.source:
        source = Path(args.source)
        if not source.exists():
            print(f"ERROR: cannot see source {source}", file=sys.stderr)
            print("If this is the saber's card, see docs/sd-card.md", file=sys.stderr)
            return 1
        paths = collect(source, {f.strip() for f in args.families.split(",") if f.strip()})
    else:
        print("ERROR: pass --source or --file", file=sys.stderr)
        return 1

    if not paths:
        print("No matching files.")
        return 0

    print(f"Files to classify: {len(paths)}")
    if len(paths) < 8:
        print("Fewer than 8 files -- calibration disabled, results are rougher.")

    started = time.time()
    classifier = Classifier()
    print(f"Model ready in {time.time() - started:.1f} s ({classifier.device})\n")

    started = time.time()
    results = classifier.classify(paths)
    elapsed = time.time() - started

    print(f"{'':<7} {'FILE':<46} {'VERDICT':<9} {'CATEGORY':<12} MARGIN")
    print("-" * 92)
    for result in results:
        path = Path(result["file"])
        label = "  ?" if not result["confident"] else ("VOICE" if result["voice"] else "   -")
        name = f"{path.parent.name}/{path.name}"
        print(f"{label:<7} {name[:46]:<46} "
              f"{'voice' if result['voice'] else 'sound':<9} "
              f"{result['category']:<12} {result['margin']:.3f}")

    confident_voice = sum(1 for r in results if r["voice"] and r["confident"])
    confident_sound = sum(1 for r in results if not r["voice"] and r["confident"])
    uncertain = sum(1 for r in results if not r["confident"])

    print(f"\n{'=' * 92}")
    print(f"voice (confident):  {confident_voice}")
    print(f"sound (confident):  {confident_sound}")
    print(f"UNCERTAIN:          {uncertain}  <- listen to these, margin < {UNCERTAIN_BELOW}")
    print(f"time:               {elapsed / len(paths):.2f} s per file")

    output = Path(args.output)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n-> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
