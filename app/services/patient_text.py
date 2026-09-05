"""Centralized patient-facing text and choice labels.

Internal workflow values remain English; this module only localizes text that
is shown to the patient. LLM-generated clinical text continues to use the
active-language prompt context directly.
"""

from __future__ import annotations

from app.services.language import normalize_language
from app.services.patient_text_full_catalog import FULL_WORKFLOW_MESSAGES


_CHOICES = {
    "en": {"yes": "Yes", "no": "No", "today": "Today", "tomorrow": "Tomorrow"},
    "hi": {"yes": "हाँ", "no": "नहीं", "today": "आज", "tomorrow": "कल"},
    "te": {"yes": "అవును", "no": "కాదు", "today": "ఈరోజు", "tomorrow": "రేపు"},
    "ta": {"yes": "ஆம்", "no": "இல்லை", "today": "இன்று", "tomorrow": "நாளை"},
    "kn": {"yes": "ಹೌದು", "no": "ಇಲ್ಲ", "today": "ಇಂದು", "tomorrow": "ನಾಳೆ"},
    "mr": {"yes": "होय", "no": "नाही", "today": "आज", "tomorrow": "उद्या"},
    "bn": {"yes": "হ্যাঁ", "no": "না", "today": "আজ", "tomorrow": "আগামীকাল"},
    "gu": {"yes": "હા", "no": "ના", "today": "આજે", "tomorrow": "કાલે"},
}

# Machine-draft locale coverage. These labels are intentionally marked below
# as pending review before they are enabled for production healthcare copy.
_DRAFT_CHOICES = {
    "pa": {"yes": "ਹਾਂ", "no": "ਨਹੀਂ", "today": "ਅੱਜ", "tomorrow": "ਕੱਲ੍ਹ"},
    "ml": {"yes": "അതെ", "no": "ഇല്ല", "today": "ഇന്ന്", "tomorrow": "നാളെ"},
    "or": {"yes": "ହଁ", "no": "ନା", "today": "ଆଜି", "tomorrow": "ଆସନ୍ତାକାଲି"},
    "ur": {"yes": "ہاں", "no": "نہیں", "today": "آج", "tomorrow": "کل"},
    "as": {"yes": "হয়", "no": "নহয়", "today": "আজি", "tomorrow": "কাইলৈ"},
    "mai": {"yes": "हँ", "no": "नहि", "today": "आइ", "tomorrow": "काल्हि"},
    "kok": {"yes": "हय", "no": "ना", "today": "आयज", "tomorrow": "फाल्यां"},
    "ne": {"yes": "हो", "no": "होइन", "today": "आज", "tomorrow": "भोलि"},
    "sd": {"yes": "ها", "no": "نه", "today": "اڄ", "tomorrow": "سڀاڻي"},
    "brx": {"yes": "जों", "no": "नङा", "today": "दिनै", "tomorrow": "फुं"},
    "doi": {"yes": "हां", "no": "नेईं", "today": "अज्ज", "tomorrow": "कल"},
    "ks": {"yes": "آ", "no": "نہ", "today": "اَز", "tomorrow": "بہ"},
    "mni": {"yes": "ꯍꯣꯏ", "no": "ꯅꯠꯇꯦ", "today": "ꯉꯥꯁꯤ", "tomorrow": "ꯀꯨꯅꯨꯡ"},
    "sa": {"yes": "आम्", "no": "न", "today": "अद्य", "tomorrow": "श्वः"},
    "sat": {"yes": "ᱦᱚᱸ", "no": "ᱵᱟᱝ", "today": "ᱛᱤᱦᱤᱧ", "tomorrow": "ᱜᱟᱯᱟ"},
    "es": {"yes": "Sí", "no": "No", "today": "Hoy", "tomorrow": "Mañana"},
    "fr": {"yes": "Oui", "no": "Non", "today": "Aujourd'hui", "tomorrow": "Demain"},
    "de": {"yes": "Ja", "no": "Nein", "today": "Heute", "tomorrow": "Morgen"},
    "it": {"yes": "Sì", "no": "No", "today": "Oggi", "tomorrow": "Domani"},
    "pt": {"yes": "Sim", "no": "Não", "today": "Hoje", "tomorrow": "Amanhã"},
    "ru": {"yes": "Да", "no": "Нет", "today": "Сегодня", "tomorrow": "Завтра"},
    "pl": {"yes": "Tak", "no": "Nie", "today": "Dzisiaj", "tomorrow": "Jutro"},
    "nl": {"yes": "Ja", "no": "Nee", "today": "Vandaag", "tomorrow": "Morgen"},
    "tr": {"yes": "Evet", "no": "Hayır", "today": "Bugün", "tomorrow": "Yarın"},
    "ar": {"yes": "نعم", "no": "لا", "today": "اليوم", "tomorrow": "غدًا"},
    "he": {"yes": "כן", "no": "לא", "today": "היום", "tomorrow": "מחר"},
    "fa": {"yes": "بله", "no": "خیر", "today": "امروز", "tomorrow": "فردا"},
    "sw": {"yes": "Ndiyo", "no": "Hapana", "today": "Leo", "tomorrow": "Kesho"},
    "el": {"yes": "Ναι", "no": "Όχι", "today": "Σήμερα", "tomorrow": "Αύριο"},
    "zh": {"yes": "是", "no": "否", "today": "今天", "tomorrow": "明天"},
    "ja": {"yes": "はい", "no": "いいえ", "today": "今日", "tomorrow": "明日"},
    "ko": {"yes": "예", "no": "아니요", "today": "오늘", "tomorrow": "내일"},
    "th": {"yes": "ใช่", "no": "ไม่ใช่", "today": "วันนี้", "tomorrow": "พรุ่งนี้"},
    "vi": {"yes": "Có", "no": "Không", "today": "Hôm nay", "tomorrow": "Ngày mai"},
    "id": {"yes": "Ya", "no": "Tidak", "today": "Hari ini", "tomorrow": "Besok"},
    "ms": {"yes": "Ya", "no": "Tidak", "today": "Hari ini", "tomorrow": "Esok"},
    "tl": {"yes": "Oo", "no": "Hindi", "today": "Ngayon", "tomorrow": "Bukas"},
    "my": {"yes": "ဟုတ်ကဲ့", "no": "မဟုတ်ပါ", "today": "ယနေ့", "tomorrow": "မနက်ဖြန်"},
    "km": {"yes": "បាទ/ចាស", "no": "ទេ", "today": "ថ្ងៃនេះ", "tomorrow": "ថ្ងៃស្អែក"},
    "si": {"yes": "ඔව්", "no": "නැහැ", "today": "අද", "tomorrow": "හෙට"},
}
_CHOICES.update(_DRAFT_CHOICES)

CATALOG_REVIEW_STATUS = {
    code: ("validated" if code in {"en", "hi", "te", "ta", "kn", "mr", "bn", "gu"} else "pending_review")
    for code in _CHOICES
}

_LABELS = {
    "en": {"doctor": "Doctor", "department": "Department", "date_time": "Date & Time", "reference": "Reference ID", "clinical_analysis": "Clinical analysis", "whats_happening": "What's happening", "why_department": "Why", "home_care": "Immediate home care", "detailed_summary": "Detailed clinical summary"},
    "hi": {"doctor": "डॉक्टर", "department": "विभाग", "date_time": "दिनांक और समय", "reference": "संदर्भ आईडी", "clinical_analysis": "क्लिनिकल विश्लेषण", "whats_happening": "क्या हो रहा है", "why_department": "क्यों", "home_care": "तुरंत घरेलू देखभाल", "detailed_summary": "विस्तृत क्लिनिकल सारांश"},
    "te": {"doctor": "వైద్యుడు", "department": "విభాగం", "date_time": "తేదీ మరియు సమయం", "reference": "రిఫరెన్స్ ఐడీ", "clinical_analysis": "క్లినికల్ విశ్లేషణ", "whats_happening": "ఏం జరుగుతోంది", "why_department": "ఎందుకు", "home_care": "తక్షణ ఇంటి సంరక్షణ", "detailed_summary": "వివరణాత్మక క్లినికల్ సారాంశం"},
    "ta": {"doctor": "மருத்துவர்", "department": "துறை", "date_time": "தேதி மற்றும் நேரம்", "reference": "குறிப்பு ஐடி", "clinical_analysis": "மருத்துவ பகுப்பாய்வு", "whats_happening": "என்ன நடக்கிறது", "why_department": "ஏன்", "home_care": "உடனடி வீட்டுப் பராமரிப்பு", "detailed_summary": "விரிவான மருத்துவ சுருக்கம்"},
    "kn": {"doctor": "ವೈದ್ಯರು", "department": "ವಿಭಾಗ", "date_time": "ದಿನಾಂಕ ಮತ್ತು ಸಮಯ", "reference": "ಉಲ್ಲೇಖ ಐಡಿ", "clinical_analysis": "ಕ್ಲಿನಿಕಲ್ ವಿಶ್ಲೇಷಣೆ", "whats_happening": "ಏನು ನಡೆಯುತ್ತಿದೆ", "why_department": "ಏಕೆ", "home_care": "ತಕ್ಷಣದ ಮನೆಯ ಆರೈಕೆ", "detailed_summary": "ವಿವರವಾದ ಕ್ಲಿನಿಕಲ್ ಸಾರಾಂಶ"},
    "mr": {"doctor": "डॉक्टर", "department": "विभाग", "date_time": "दिनांक आणि वेळ", "reference": "संदर्भ आयडी", "clinical_analysis": "क्लिनिकल विश्लेषण", "whats_happening": "काय होत आहे", "why_department": "का", "home_care": "तात्काळ घरची काळजी", "detailed_summary": "सविस्तर क्लिनिकल सारांश"},
    "bn": {"doctor": "ডাক্তার", "department": "বিভাগ", "date_time": "তারিখ ও সময়", "reference": "রেফারেন্স আইডি", "clinical_analysis": "ক্লিনিক্যাল বিশ্লেষণ", "whats_happening": "কী ঘটছে", "why_department": "কেন", "home_care": "তাৎক্ষণিক বাড়ির যত্ন", "detailed_summary": "বিস্তারিত ক্লিনিক্যাল সারাংশ"},
    "gu": {"doctor": "ડૉક્ટર", "department": "વિભાગ", "date_time": "તારીખ અને સમય", "reference": "સંદર્ભ આઈડી", "clinical_analysis": "ક્લિનિકલ વિશ્લેષણ", "whats_happening": "શું થઈ રહ્યું છે", "why_department": "શા માટે", "home_care": "તાત્કાલિક ઘરેલુ સંભાળ", "detailed_summary": "વિગતવાર ક્લિનિકલ સારાંશ"},
}


_MESSAGES = {
    "department_booking_prompt": {
        "en": "Would you like to book an appointment with a {department} doctor? ({yes} / {no})",
        "hi": "क्या आप {department} डॉक्टर के साथ अपॉइंटमेंट बुक करना चाहेंगे? ({yes} / {no})",
        "te": "మీరు {department} వైద్యుడితో అపాయింట్‌మెంట్ బుక్ చేసుకోవాలనుకుంటున్నారా? ({yes} / {no})",
        "ta": "{department} மருத்துவரிடம் அப்பாயின்ட்மென்ட் பதிவு செய்ய விரும்புகிறீர்களா? ({yes} / {no})",
        "kn": "ನೀವು {department} ವೈದ್ಯರೊಂದಿಗೆ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬುಕ್ ಮಾಡಲು ಬಯಸುವಿರಾ? ({yes} / {no})",
        "mr": "तुम्हाला {department} डॉक्टरांकडे अपॉइंटमेंट बुक करायची आहे का? ({yes} / {no})",
        "bn": "আপনি কি {department} ডাক্তারের সঙ্গে অ্যাপয়েন্টমেন্ট বুক করতে চান? ({yes} / {no})",
        "gu": "શું તમે {department} ડૉક્ટર સાથે એપોઇન્ટમેન્ટ બુક કરવા માંગો છો? ({yes} / {no})",
    },
    "booking_prompt": {
        "en": "Would you like me to find available appointment slots for you? ({yes} / {no})",
        "hi": "क्या मैं आपके लिए उपलब्ध अपॉइंटमेंट स्लॉट ढूँढूँ? ({yes} / {no})",
        "te": "మీ కోసం అందుబాటులో ఉన్న అపాయింట్‌మెంట్ సమయాలను కనుగొనాలా? ({yes} / {no})",
        "ta": "உங்களுக்கான கிடைக்கக்கூடிய அப்பாயின்ட்மென்ட் நேரங்களைத் தேடவா? ({yes} / {no})",
        "kn": "ನಿಮಗಾಗಿ ಲಭ್ಯವಿರುವ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಸಮಯಗಳನ್ನು ಹುಡುಕಬೇಕೇ? ({yes} / {no})",
        "mr": "तुमच्यासाठी उपलब्ध अपॉइंटमेंट स्लॉट शोधू का? ({yes} / {no})",
        "bn": "আপনার জন্য উপলব্ধ অ্যাপয়েন্টমেন্টের সময় খুঁজে দেব কি? ({yes} / {no})",
        "gu": "શું હું તમારા માટે ઉપલબ્ધ એપોઇન્ટમેન્ટ સમય શોધું? ({yes} / {no})",
    },
    "booking_declined": {
        "en": "No problem. If you change your mind or feel worse, you can start a new chat. Take care and rest well!",
        "hi": "कोई बात नहीं। यदि आपका मन बदल जाए या आपको अधिक परेशानी हो, तो आप नई चैट शुरू कर सकते हैं। अपना ध्यान रखें और आराम करें!",
        "te": "పర్వాలేదు. మీ అభిప్రాయం మారినా లేదా మీకు మరింత ఇబ్బందిగా అనిపించినా, కొత్త చాట్‌ను ప్రారంభించవచ్చు. జాగ్రత్తగా ఉండండి, విశ్రాంతి తీసుకోండి!",
        "ta": "பரவாயில்லை. உங்கள் எண்ணம் மாறினால் அல்லது உடல்நிலை மோசமடைந்தால், புதிய உரையாடலைத் தொடங்கலாம். கவனமாக இருந்து ஓய்வெடுக்கவும்!",
        "kn": "ಪರವಾಗಿಲ್ಲ. ನಿಮ್ಮ ಮನಸ್ಸು ಬದಲಾದರೆ ಅಥವಾ ನಿಮಗೆ ಹೆಚ್ಚು ತೊಂದರೆಯಾದರೆ, ಹೊಸ ಚಾಟ್ ಪ್ರಾರಂಭಿಸಬಹುದು. ಕಾಳಜಿ ವಹಿಸಿ ಮತ್ತು ವಿಶ್ರಾಂತಿ ಪಡೆಯಿರಿ!",
        "mr": "काही हरकत नाही. तुमचा विचार बदलला किंवा त्रास वाढला तर तुम्ही नवीन चॅट सुरू करू शकता. काळजी घ्या आणि विश्रांती घ्या!",
        "bn": "কোনও সমস্যা নেই। আপনার মত বদলালে বা অসুস্থতা বাড়লে নতুন চ্যাট শুরু করতে পারেন। নিজের যত্ন নিন এবং বিশ্রাম নিন!",
        "gu": "કોઈ વાંધો નથી. તમારો વિચાર બદલાય અથવા તકલીફ વધે તો તમે નવી ચેટ શરૂ કરી શકો છો. તમારી સંભાળ રાખો અને આરામ કરો!",
    },
    "report_forward_prompt": {
        "en": "Should I forward your detailed clinical report to {doctor} before your appointment?\n\nThis will include the symptoms, patterns, triggers, and recommendations we discussed. ({yes} / {no})",
        "hi": "क्या मैं आपकी अपॉइंटमेंट से पहले आपकी विस्तृत क्लिनिकल रिपोर्ट {doctor} को भेज दूँ?\n\nइसमें आपके लक्षण, पैटर्न, कारण और हमारी चर्चा की गई सलाह शामिल होगी। ({yes} / {no})",
        "te": "మీ అపాయింట్‌మెంట్‌కు ముందు మీ వివరణాత్మక క్లినికల్ నివేదికను {doctor}కు పంపాలా?\n\nఇందులో మీ లక్షణాలు, నమూనాలు, కారణాలు మరియు మనం చర్చించిన సూచనలు ఉంటాయి. ({yes} / {no})",
        "ta": "உங்கள் அப்பாயின்ட்மென்ட்டுக்கு முன் உங்கள் விரிவான மருத்துவ அறிக்கையை {doctor}க்கு அனுப்பவா?\n\nஇதில் உங்கள் அறிகுறிகள், முறைகள், காரணிகள் மற்றும் நாம் பேசிய பரிந்துரைகள் அடங்கும். ({yes} / {no})",
        "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್‌ಗೂ ಮುನ್ನ ನಿಮ್ಮ ವಿವರವಾದ ಕ್ಲಿನಿಕಲ್ ವರದಿಯನ್ನು {doctor} ಅವರಿಗೆ ಕಳುಹಿಸಬೇಕೇ?\n\nಇದರಲ್ಲಿ ನಿಮ್ಮ ಲಕ್ಷಣಗಳು, ಮಾದರಿಗಳು, ಕಾರಣಗಳು ಮತ್ತು ನಾವು ಚರ್ಚಿಸಿದ ಸಲಹೆಗಳು ಇರುತ್ತವೆ. ({yes} / {no})",
        "mr": "तुमच्या अपॉइंटमेंटपूर्वी तुमचा सविस्तर क्लिनिकल अहवाल {doctor} यांना पाठवू का?\n\nयात तुमची लक्षणे, नमुने, कारणे आणि आपण चर्चा केलेल्या सूचना असतील. ({yes} / {no})",
        "bn": "আপনার অ্যাপয়েন্টমেন্টের আগে কি আপনার বিস্তারিত ক্লিনিক্যাল রিপোর্ট {doctor}-কে পাঠাব?\n\nএতে আপনার উপসর্গ, ধরন, কারণ এবং আমাদের আলোচিত পরামর্শ থাকবে। ({yes} / {no})",
        "gu": "તમારી એપોઇન્ટમેન્ટ પહેલાં તમારો વિગતવાર ક્લિનિકલ રિપોર્ટ {doctor}ને મોકલું?\n\nતેમાં તમારા લક્ષણો, પેટર્ન, કારણો અને આપણે ચર્ચા કરેલી સલાહ હશે. ({yes} / {no})",
    },
    "appointment_confirmed": {
        "en": "Your appointment is booked and confirmed!",
        "hi": "आपकी अपॉइंटमेंट बुक और कन्फर्म हो गई है!",
        "te": "మీ అపాయింట్‌మెంట్ బుక్ చేసి నిర్ధారించబడింది!",
        "ta": "உங்கள் அப்பாயின்ட்மென்ட் பதிவு செய்யப்பட்டு உறுதிசெய்யப்பட்டது!",
        "kn": "ನಿಮ್ಮ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬುಕ್ ಮಾಡಿ ದೃಢಪಡಿಸಲಾಗಿದೆ!",
        "mr": "तुमची अपॉइंटमेंट बुक आणि निश्चित झाली आहे!",
        "bn": "আপনার অ্যাপয়েন্টমেন্ট বুক এবং নিশ্চিত হয়েছে!",
        "gu": "તમારી એપોઇન્ટમેન્ટ બુક અને કન્ફર્મ થઈ ગઈ છે!",
    },
    "report_sent": {
        "en": "Clinical report sent!",
        "hi": "क्लिनिकल रिपोर्ट भेज दी गई है!",
        "te": "క్లినికల్ నివేదిక పంపబడింది!",
        "ta": "மருத்துவ அறிக்கை அனுப்பப்பட்டது!",
        "kn": "ಕ್ಲಿನಿಕಲ್ ವರದಿ ಕಳುಹಿಸಲಾಗಿದೆ!",
        "mr": "क्लिनिकल अहवाल पाठवला आहे!",
        "bn": "ক্লিনিক্যাল রিপোর্ট পাঠানো হয়েছে!",
        "gu": "ક્લિનિકલ રિપોર્ટ મોકલવામાં આવ્યો છે!",
    },
}

# The base catalog above contains the originally validated Wave 1 copy. The
# expanded static catalog supplies the same workflow keys for every registered
# locale without adding runtime translation calls to patient interactions.
for _locale, _locale_messages in FULL_WORKFLOW_MESSAGES.items():
    for _message_key, _template in _locale_messages.items():
        _MESSAGES.setdefault(_message_key, {})[_locale] = _template
_MESSAGES.update({
    "cancellation_prompt": {
        "en": "Would you like to cancel your appointment with {doctor} on {date_time}? ({yes} / {no})",
    },
    "cancellation_confirmed": {
        "en": "Your appointment with {doctor} on {date_time} has been cancelled.",
    },
    "reschedule_prompt": {
        "en": "Would you like to reschedule your appointment with {doctor}? ({yes} / {no})",
    },
    "slot_error": {
        "en": "That appointment slot is no longer available. Please choose another slot.",
    },
    "selection_error": {
        "en": "I could not understand that selection. Please choose one of the displayed options.",
    },
})

# Restore non-English entries for keys whose English defaults were added above.
for _locale, _locale_messages in FULL_WORKFLOW_MESSAGES.items():
    for _message_key, _template in _locale_messages.items():
        _MESSAGES.setdefault(_message_key, {})[_locale] = _template


def patient_language(state: dict | None) -> str:
    return normalize_language((state or {}).get("active_language")) or normalize_language((state or {}).get("preferred_language")) or "en"


def choice_label(state_or_language: dict | str | None, choice: str) -> str:
    code = patient_language(state_or_language) if isinstance(state_or_language, dict) or state_or_language is None else normalize_language(state_or_language) or "en"
    return _CHOICES.get(code, _CHOICES["en"]).get(choice, choice)


def is_localized_choice(text: str | None, choice: str) -> bool:
    """Match a patient-facing choice label while keeping its internal value stable."""
    normalized = " ".join((text or "").strip().casefold().split())
    if not normalized:
        return False
    return any(
        normalized == " ".join(str(label).casefold().split())
        for labels in _CHOICES.values()
        for key, label in labels.items()
        if key == choice
    )


def display_label(state_or_language: dict | str | None, label: str) -> str:
    code = patient_language(state_or_language) if isinstance(state_or_language, dict) or state_or_language is None else normalize_language(state_or_language) or "en"
    return _LABELS.get(code, _LABELS["en"]).get(label, label)


def patient_message(state: dict | None, key: str, **values: object) -> str:
    code = patient_language(state)
    template = _MESSAGES.get(key, {}).get(code) or _MESSAGES.get(key, {}).get("en") or key
    # Catalog entries can contain workflow placeholders shared by multiple
    # branches. Keep the patient flow alive if a legacy caller omits one while
    # still allowing callers to provide the real appointment values.
    values.setdefault("doctor", "your doctor")
    values.setdefault("date_time", "your appointment")
    values.setdefault("reference", "your appointment reference")
    values.setdefault("department", "the selected department")
    values.setdefault("yes", choice_label(code, "yes"))
    values.setdefault("no", choice_label(code, "no"))
    return template.format(**values)
