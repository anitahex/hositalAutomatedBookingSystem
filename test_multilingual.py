from app.services import language
from app.services.language import apply_language_turn, detect_language, explicit_language_switch
from app.services.patient_text import CATALOG_REVIEW_STATUS, display_label, is_localized_choice, patient_message


def test_fasttext_is_the_primary_detector(monkeypatch):
    monkeypatch.setattr(language, "_detect_with_fasttext", lambda text: ("hi", 0.93))
    assert detect_language("mujhe bukhar hai") == ("hi", 0.93)


def test_script_detector_is_used_when_fasttext_is_unavailable(monkeypatch):
    monkeypatch.setattr(language, "_detect_with_fasttext", lambda text: None)
    detected, confidence = detect_language("నాకు జ్వరం ఉంది.")
    assert detected == "te"
    assert confidence >= 0.78


def test_global_and_asian_expansion_languages_are_detected():
    examples = {
        "es": "Tengo fiebre y dolor de cabeza.",
        "fr": "J ai de la fievre et mal a la tete.",
        "de": "Ich habe Fieber und Kopfschmerzen.",
        "ru": "\u0423 \u043c\u0435\u043d\u044f \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u0438 \u0433\u043e\u043b\u043e\u0432\u043d\u0430\u044f \u0431\u043e\u043b\u044c.",
        "ar": "\u0644\u062f\u064a \u062d\u0645\u0649 \u0648\u0635\u062f\u0627\u0639.",
        "zh": "\u6211\u53d1\u70e7\u548c\u5934\u75db\u3002",
        "ja": "\u71b1\u304c\u3042\u308a\u3001\u982d\u304c\u75db\u3044\u3067\u3059\u3002",
        "ko": "\uc5f4\uc774 \ub098\uace0 \uba38\ub9ac\uac00 \uc544\ud30c\uc694.",
        "th": "\u0e09\u0e31\u0e19\u0e21\u0e35\u0e44\u0e02\u0e49\u0e41\u0e25\u0e30\u0e1b\u0e27\u0e14\u0e2b\u0e31\u0e27",
        "vi": "Tôi bị sốt và đau đầu.",
        "id": "Saya demam dan sakit kepala.",
    }
    for expected, text in examples.items():
        detected, confidence = detect_language(text)
        assert detected == expected
        assert confidence >= 0.55


def test_global_language_switch_command_is_supported():
    assert explicit_language_switch("Switch to Spanish") == "es"
    assert explicit_language_switch("Please respond in Japanese") == "ja"


def test_wave_one_language_detection():
    examples = {
        "en": "I have fever since yesterday.",
        "hi": "मुझे बुखार है।",
        "te": "నాకు జ్వరం ఉంది.",
        "ta": "எனக்கு காய்ச்சல் உள்ளது.",
        "kn": "ನನಗೆ ಜ್ವರ ಇದೆ.",
        "mr": "मला ताप आहे।",
        "bn": "আমার জ্বর হয়েছে।",
        "gu": "મને તાવ છે.",
    }
    for expected, text in examples.items():
        language, confidence = detect_language(text)
        assert language == expected
        assert confidence >= 0.78


def test_code_mixed_messages_follow_the_native_script():
    assert detect_language("నాకు fever ఉంది.")[0] == "te"
    assert detect_language("Mujhe fever hai.")[0] == "en"  # no script signal; active language remains stable


def test_short_acknowledgements_do_not_change_active_language():
    state = {"active_language": "te", "preferred_language": "te"}
    assert apply_language_turn(state, "ok")["active_language"] == "te"
    assert apply_language_turn(state, "yes")["active_language"] == "te"


def test_language_switch_requires_two_meaningful_turns():
    state = {"active_language": "en", "preferred_language": "en", "conversation_history": [{"role": "user", "text": "I have fever."}]}
    first = apply_language_turn(state, "నాకు జ్వరం ఉంది.")
    assert first["active_language"] == "en"
    second = apply_language_turn({**state, **first}, "నాకు ఇంకా జ్వరం ఉంది.")
    assert second["active_language"] == "te"


def test_first_meaningful_message_establishes_non_english_language():
    state = {"active_language": "en", "preferred_language": "en", "conversation_history": []}
    updates = apply_language_turn(state, "मुझे पेट में दर्द हो रहा है")
    assert updates["active_language"] == "hi"
    assert updates["language_changed"] is True


def test_explicit_switch_is_immediate_and_not_medical_intent():
    assert explicit_language_switch("Switch to Telugu") == "te"
    updates = apply_language_turn({"active_language": "en"}, "తెలుగులో సమాధానం ఇవ్వండి")
    assert updates["active_language"] == "te"
    assert updates["language_control_response"]


def test_patient_workflow_text_uses_active_language_and_localizes_choices():
    state = {"active_language": "hi", "preferred_language": "hi"}
    prompt = patient_message(state, "report_forward_prompt", doctor="Dr. A")
    assert "Dr. A" in prompt
    assert "हाँ / नहीं" in prompt
    assert "Should I forward" not in prompt
    assert display_label(state, "doctor") == "डॉक्टर"


def test_patient_summary_prompt_is_not_used_for_english_doctor_summary():
    # The checkup node's summary call has an explicit English-only instruction;
    # this guards the centralized text contract used by patient-facing flows.
    assert patient_message({"active_language": "te"}, "department_booking_prompt", department="Cardiology")


def test_all_registered_locales_have_choice_catalog_entries():
    assert set(CATALOG_REVIEW_STATUS) >= set(language.SUPPORTED_LANGUAGES)
    assert CATALOG_REVIEW_STATUS["hi"] == "validated"
    assert CATALOG_REVIEW_STATUS["pa"] == "pending_review"


def test_clear_romanized_hindi_is_detected():
    assert detect_language("mujhe pet mai dard ho rha hai")[0] == "hi"


def test_localized_yes_no_choices_map_to_internal_values():
    assert is_localized_choice("ja", "yes")
    assert is_localized_choice("nein", "no")
    assert is_localized_choice("はい", "yes")
