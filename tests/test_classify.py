"""Tests for the speech-vs-sound classifier's decision logic.

These cover the maths only -- no model is loaded. The model's accuracy is a
separate, empirical question answered by running it against files whose answer
you already know (see docs/sound-anatomy.md).
"""

import numpy as np

from tools.classify import aggregate_by_category, calibrate, verdict

VOICE = {"speech", "vocalization"}


def test_calibrate_neutralises_a_label_that_matches_everything():
    """A label scoring high on every file carries no information.

    Without this correction one broad label ("a short electric zap") won 14 of
    24 files in testing, including every single blade clash. Subtracting each
    label's mean across the corpus removes that advantage.
    """
    raw = np.array([[0.1, 0.9], [0.2, 0.9], [0.3, 0.9]])
    calibrated = calibrate(raw)
    assert calibrated[:, 1].max() == 0.0
    assert calibrated[2, 0] > calibrated[0, 0]


def test_calibrate_preserves_relative_order_within_a_label():
    raw = np.array([[0.1, 0.5], [0.4, 0.2]])
    calibrated = calibrate(raw)
    assert calibrated[1, 0] > calibrated[0, 0]


def test_aggregate_takes_the_best_label_per_category():
    row = np.array([0.1, 0.5, 0.2])
    categories = ["speech", "speech", "hum"]
    assert aggregate_by_category(row, categories) == {"speech": 0.5, "hum": 0.2}


def test_verdict_reports_voice_when_a_voice_category_wins():
    result = verdict({"speech": 0.4, "hum": 0.1}, VOICE, threshold=0.05)
    assert result["voice"] is True
    assert result["confident"] is True


def test_verdict_reports_sound_when_a_sound_category_wins():
    result = verdict({"speech": 0.1, "hum": 0.4}, VOICE, threshold=0.05)
    assert result["voice"] is False
    assert result["confident"] is True


def test_verdict_flags_uncertainty_on_a_narrow_margin():
    """The one binary error in testing had a margin of 0.014.

    Anything that close is handed to a human rather than guessed at.
    """
    result = verdict({"speech": 0.104, "hum": 0.100}, VOICE, threshold=0.05)
    assert result["confident"] is False


def test_margin_compares_voice_against_sound_not_top_two():
    """'speech' vs 'vocalization' is an argument INSIDE one answer.

    Both mean a human is audible. Treating their closeness as uncertainty would
    flag confident results as doubtful, so the margin is measured between the
    best voice score and the best sound score.
    """
    result = verdict({"speech": 0.30, "vocalization": 0.29, "hum": 0.01},
                     VOICE, threshold=0.05)
    assert result["voice"] is True
    assert result["confident"] is True


def test_verdict_names_the_winning_category():
    result = verdict({"speech": 0.1, "clash": 0.6, "hum": 0.2}, VOICE, threshold=0.05)
    assert result["category"] == "clash"
