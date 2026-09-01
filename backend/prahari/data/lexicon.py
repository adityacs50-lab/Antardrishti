"""Field vocabulary for synthetic OIL report generation.

Everything in here is surface form: how an Indian upstream worker or supervisor
in Upper Assam actually writes an unsafe-act, unsafe-condition or near-miss
report. It carries no labels and no safety semantics - it exists purely to make
generated text look like the real thing, so that a model trained or evaluated
on it is not learning a register that does not exist in the field.

Code-mixing is modelled as parallel phrase banks keyed by MEANING, so the same
semantic slot can be realised in English, romanised Hindi, Devanagari Hindi,
romanised Assamese or Assamese script. That is how the actual reports read:
one sentence will switch script mid-clause and switch back.
"""

from __future__ import annotations

from enum import Enum

# --------------------------------------------------------------------------
# Places, installations, people
# --------------------------------------------------------------------------

#: Real Oil India Limited operational areas in Upper Assam.
LOCATIONS: tuple[str, ...] = (
    "Naoholia",
    "Baghjan",
    "Duliajan",
    "Moran",
    "Kusijan",
    "Dikom",
    "Jorajan",
    "Madhuban",
    "Tengakhat",
    "Hebeda",
)

INSTALLATION_TEMPLATES: tuple[str, ...] = (
    "Rig No. {rig}",
    "Rig-{rig}",
    "rig no {rig}",
    "GGS-{small}",
    "GGS {small}",
    "OCS-{small}",
    "EPS-{small}",
    "Well No. {well}",
    "well {well}",
    "Workover Rig No. {rig}",
    "WO Rig-{rig}",
    "Pump Station-{small}",
    "Pipeline ROW KM {km}",
    "CTF-{small}",
)

DESIGNATIONS: tuple[str, ...] = (
    "roustabout",
    "derrickman",
    "floorman",
    "fitter",
    "rigman",
    "welder",
    "helper",
    "khalasi",
    "operator",
    "electrician",
    "driller",
    "asst. driller",
    "crane operator",
    "rigger",
    "technician",
    "mazdoor",
)

REPORTER_DESIGNATIONS: tuple[str, ...] = (
    "Safety Officer",
    "Sr. Safety Officer",
    "Installation Manager",
    "Tool Pusher",
    "Field Supervisor",
    "Shift In-charge",
    "HSE Coordinator",
    "Company Man",
    "Area Manager",
    "Jr. Engineer",
)

#: Assamese and Indian surnames common in the Upper Assam workforce.
SURNAMES: tuple[str, ...] = (
    "Gogoi", "Bora", "Saikia", "Dutta", "Baruah", "Hazarika", "Phukan",
    "Das", "Sharma", "Nath", "Kalita", "Rajkhowa", "Chetia", "Konwar",
    "Tanti", "Bhuyan", "Deka", "Mahanta", "Sonowal", "Yadav", "Singh",
    "Prasad", "Kumar", "Mandal", "Rabha", "Moran", "Doley", "Pegu",
)

INITIALS: tuple[str, ...] = ("A", "B", "D", "G", "H", "J", "K", "M", "N", "P", "R", "S", "T")

HONORIFICS: tuple[str, ...] = ("Sri", "Shri", "Mr.", "Sri.", "")

CONTRACTOR_PHRASES: tuple[str, ...] = (
    "contractor crew",
    "contractual workman",
    "contractor workman",
    "cont. labour",
    "party workman",
    "third party crew",
    "contractor's man",
)


class LanguageMix(str, Enum):
    """How much and which non-English material the report carries."""

    ENGLISH = "english"
    HINGLISH = "hinglish"
    HINDI_DEVANAGARI = "hindi_devanagari"
    ASSAMESE_ROMAN = "assamese_roman"
    ASSAMESE_SCRIPT = "assamese_script"
    HEAVY_CODE_MIX = "heavy_code_mix"


class WritingStyle(str, Enum):
    """Register of the report author."""

    TERSE_TELEGRAPHIC = "terse_telegraphic"
    SUPERVISOR_FORMAL = "supervisor_formal"
    RAMBLING = "rambling"
    TWO_LINE_VAGUE = "two_line_vague"


# --------------------------------------------------------------------------
# Parallel phrase banks, keyed by meaning
# --------------------------------------------------------------------------
# Order within each tuple: ENGLISH, HINGLISH (romanised Hindi),
# HINDI_DEVANAGARI, ASSAMESE_ROMAN, ASSAMESE_SCRIPT.

PHRASE_BANK: dict[str, dict[LanguageMix, tuple[str, ...]]] = {
    "was_working": {
        LanguageMix.ENGLISH: ("was working", "was engaged in the job", "was doing the job"),
        LanguageMix.HINGLISH: ("kaam kar raha tha", "job kar raha tha", "duty pe tha"),
        LanguageMix.HINDI_DEVANAGARI: ("काम कर रहा था", "ड्यूटी पर था"),
        LanguageMix.ASSAMESE_ROMAN: ("kaam kori asil", "kaam kori thakute"),
        LanguageMix.ASSAMESE_SCRIPT: ("কাম কৰি আছিল", "কাম কৰি থকা সময়ত"),
    },
    "no_safety_belt": {
        LanguageMix.ENGLISH: (
            "was not wearing safety belt",
            "without full body harness",
            "safety harness not worn",
        ),
        LanguageMix.HINGLISH: (
            "safety belt nahi pehna tha",
            "harness nahi laga tha",
            "belt pehne bina kaam kar raha tha",
        ),
        LanguageMix.HINDI_DEVANAGARI: ("सेफ्टी बेल्ट नहीं पहना था", "हारनेस नहीं लगाया था"),
        LanguageMix.ASSAMESE_ROMAN: ("safety belt pindhi noasil", "harness loga nasil"),
        LanguageMix.ASSAMESE_SCRIPT: ("নিৰাপত্তা বেল্ট পিন্ধা নাছিল",),
    },
    "no_permit": {
        LanguageMix.ENGLISH: (
            "permit was not taken",
            "work permit not available at site",
            "no valid PTW",
        ),
        LanguageMix.HINGLISH: ("permit nahi liya", "PTW nahi tha", "permit ka copy site pe nahi tha"),
        LanguageMix.HINDI_DEVANAGARI: ("परमिट नहीं लिया", "परमिट साइट पर नहीं था"),
        LanguageMix.ASSAMESE_ROMAN: ("permit loa nasil", "PTW nasil"),
        LanguageMix.ASSAMESE_SCRIPT: ("অনুমতি পত্ৰ লোৱা নাছিল",),
    },
    "no_gas_test": {
        LanguageMix.ENGLISH: ("gas test was not done", "gas testing not carried out"),
        LanguageMix.HINGLISH: ("gas check nahi hua", "gas test nahi kiya tha"),
        LanguageMix.HINDI_DEVANAGARI: ("गैस चेक नहीं हुआ", "गैस टेस्ट नहीं किया"),
        LanguageMix.ASSAMESE_ROMAN: ("gas check hoa nasil",),
        LanguageMix.ASSAMESE_SCRIPT: ("গেছ পৰীক্ষা কৰা হোৱা নাছিল",),
    },
    "no_injury": {
        LanguageMix.ENGLISH: (
            "No injury occurred",
            "no one was injured",
            "No injury to personnel",
            "Nobody got hurt",
        ),
        LanguageMix.HINGLISH: ("koi chot nahi lagi", "kisi ko chot nahi aayi", "koi injury nahi hui"),
        LanguageMix.HINDI_DEVANAGARI: ("कोई चोट नहीं लगी", "किसी को चोट नहीं आई"),
        LanguageMix.ASSAMESE_ROMAN: ("eku aghat poa nai", "kunu manuh aghat poa nai"),
        LanguageMix.ASSAMESE_SCRIPT: ("কোনো আঘাত হোৱা নাই",),
    },
    "was_in_hurry": {
        LanguageMix.ENGLISH: ("was in a hurry", "was rushing to finish the job"),
        LanguageMix.HINGLISH: ("jaldi mein tha", "jaldbazi kar raha tha", "shift khatam karne ki jaldi thi"),
        LanguageMix.HINDI_DEVANAGARI: ("जल्दी में था", "जल्दबाजी कर रहा था"),
        LanguageMix.ASSAMESE_ROMAN: ("khonge khonge kaam kori asil",),
        LanguageMix.ASSAMESE_SCRIPT: ("খৰখেদাকৈ কাম কৰি আছিল",),
    },
    "informed_supervisor": {
        LanguageMix.ENGLISH: ("supervisor was informed", "reported to shift in-charge"),
        LanguageMix.HINGLISH: ("supervisor ko bataya", "in-charge ko inform kiya"),
        LanguageMix.HINDI_DEVANAGARI: ("सुपरवाइजर को बताया", "इंचार्ज को सूचित किया"),
        LanguageMix.ASSAMESE_ROMAN: ("supervisor k koisilo", "in-charge k jonoa hol"),
        LanguageMix.ASSAMESE_SCRIPT: ("চুপাৰভাইজাৰক জনোৱা হ'ল",),
    },
    "job_stopped": {
        LanguageMix.ENGLISH: ("Job was stopped immediately", "Work stopped", "Activity was halted"),
        LanguageMix.HINGLISH: ("kaam turant band kara diya", "job rok diya gaya"),
        LanguageMix.HINDI_DEVANAGARI: ("काम तुरंत बंद करा दिया", "काम रोक दिया गया"),
        LanguageMix.ASSAMESE_ROMAN: ("kaam bondho kora hol", "logote kaam bondho kora hol"),
        LanguageMix.ASSAMESE_SCRIPT: ("কাম বন্ধ কৰা হ'ল",),
    },
    "was_standing_under": {
        LanguageMix.ENGLISH: ("was standing under the load", "was positioned below the suspended load"),
        LanguageMix.HINGLISH: ("load ke niche khada tha", "load ke neeche aa gaya"),
        LanguageMix.HINDI_DEVANAGARI: ("लोड के नीचे खड़ा था",),
        LanguageMix.ASSAMESE_ROMAN: ("load r tolot thiy hoi asil",),
        LanguageMix.ASSAMESE_SCRIPT: ("বোজাৰ তলত থিয় হৈ আছিল",),
    },
    "did_not_check": {
        LanguageMix.ENGLISH: ("did not check", "no pre-use inspection was done"),
        LanguageMix.HINGLISH: ("check nahi kiya", "dekha hi nahi", "inspection nahi kiya tha"),
        LanguageMix.HINDI_DEVANAGARI: ("चेक नहीं किया", "जाँच नहीं की"),
        LanguageMix.ASSAMESE_ROMAN: ("check kora nasil",),
        LanguageMix.ASSAMESE_SCRIPT: ("পৰীক্ষা কৰা হোৱা নাছিল",),
    },
    "condition_bad": {
        LanguageMix.ENGLISH: ("condition was poor", "found in defective condition", "was damaged"),
        LanguageMix.HINGLISH: ("condition kharab tha", "halat theek nahi tha", "tuta hua tha"),
        LanguageMix.HINDI_DEVANAGARI: ("हालत खराब थी", "टूटा हुआ था"),
        LanguageMix.ASSAMESE_ROMAN: ("bhal nasil", "kharap oi asil"),
        LanguageMix.ASSAMESE_SCRIPT: ("ভাল নাছিল", "বেয়া অৱস্থাত আছিল"),
    },
    "was_advised": {
        LanguageMix.ENGLISH: ("Workman was counselled", "Advised on the spot", "Counselling given"),
        LanguageMix.HINGLISH: ("samjha diya gaya", "warning di gayi", "usko samjhaya"),
        LanguageMix.HINDI_DEVANAGARI: ("समझा दिया गया", "चेतावनी दी गई"),
        LanguageMix.ASSAMESE_ROMAN: ("buja diya hol", "sotorko kora hol"),
        LanguageMix.ASSAMESE_SCRIPT: ("সতৰ্ক কৰা হ'ল",),
    },
    "narrow_escape": {
        LanguageMix.ENGLISH: ("Narrow escape", "It was a close call", "Luckily nobody was there"),
        LanguageMix.HINGLISH: ("bal bal bacha", "bada haadsa hone se bach gaya", "kismat achhi thi"),
        LanguageMix.HINDI_DEVANAGARI: ("बाल बाल बचा", "बड़ा हादसा होने से बच गया"),
        LanguageMix.ASSAMESE_ROMAN: ("olop tore bosi gol", "dangor durghotona ekhon hobo parisil"),
        LanguageMix.ASSAMESE_SCRIPT: ("ডাঙৰ দুৰ্ঘটনা এখন হ'ব পাৰিলেহেঁতেন",),
    },
    "suddenly": {
        LanguageMix.ENGLISH: ("suddenly", "all of a sudden", "without warning"),
        LanguageMix.HINGLISH: ("achanak", "ekdum se"),
        LanguageMix.HINDI_DEVANAGARI: ("अचानक",),
        LanguageMix.ASSAMESE_ROMAN: ("hothat",),
        LanguageMix.ASSAMESE_SCRIPT: ("হঠাৎ",),
    },
    "everything_ok": {
        LanguageMix.ENGLISH: ("everything was found in order", "all controls were in place"),
        LanguageMix.HINGLISH: ("sab theek tha", "sab kuch sahi paya gaya"),
        LanguageMix.HINDI_DEVANAGARI: ("सब ठीक था",),
        LanguageMix.ASSAMESE_ROMAN: ("sokolu thik asil",),
        LanguageMix.ASSAMESE_SCRIPT: ("সকলো ঠিক আছিল",),
    },
}


# --------------------------------------------------------------------------
# Noise: abbreviations, typos, formatting quirks
# --------------------------------------------------------------------------

#: Expansions the field never writes out in full.
ABBREVIATION_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ("personal protective equipment", "PPE"),
    ("permit to work", "PTW"),
    ("lock out tag out", "LOTO"),
    ("lockout tagout", "LOTO"),
    ("working at height", "WAH"),
    ("job safety analysis", "JSA"),
    ("blowout preventer", "BOP"),
    ("group gathering station", "GGS"),
    ("oil collecting station", "OCS"),
    ("early production system", "EPS"),
    ("hydrogen sulphide", "H2S"),
    ("standard operating procedure", "SOP"),
    ("toolbox talk", "TBT"),
    ("right of way", "ROW"),
    ("self contained breathing apparatus", "SCBA"),
    ("pressure safety valve", "PSV"),
    ("approximately", "approx"),
    ("about", "abt"),
    ("number", "no."),
    ("numbers", "nos"),
    ("metre", "mtr"),
    ("metres", "mtr"),
    ("with", "w/"),
    ("without", "w/o"),
    ("hours", "hrs"),
    ("equipment", "eqpt"),
    ("maintenance", "mtce"),
)

#: Misspellings that recur in real Indian industrial reporting.
COMMON_MISSPELLINGS: tuple[tuple[str, str], ...] = (
    ("received", "recieved"),
    ("occurred", "occured"),
    ("separate", "seperate"),
    ("maintenance", "maintainance"),
    ("equipment", "equipement"),
    ("safety", "safty"),
    ("immediately", "immediatly"),
    ("personnel", "personel"),
    ("advised", "adviced"),
    ("negligence", "negligance"),
    ("supervisor", "supervisior"),
    ("accident", "accidnet"),
    ("pressure", "presure"),
    ("scaffold", "scaffhold"),
    ("harness", "harnes"),
    ("vehicle", "vehical"),
    ("labour", "labor"),
    ("careless", "carless"),
)

TIME_FORMATS: tuple[str, ...] = (
    "{h:02d}{m:02d} hrs",
    "{h:02d}:{m:02d} hrs",
    "abt {h:02d}{m:02d} hrs",
    "around {h:02d}{m:02d} hrs",
    "{h:02d}.{m:02d} hrs",
    "approx {h:02d}{m:02d}hrs",
)

DATE_FORMATS: tuple[str, ...] = (
    "{d:02d}.{mo:02d}.{y}",
    "{d:02d}/{mo:02d}/{y}",
    "{d:02d}-{mo:02d}-{y}",
    "{d:02d}.{mo:02d}.{y2:02d}",
)

REPORT_OPENERS: tuple[str, ...] = (
    "On {date} at {time},",
    "On {date} during {shift} shift,",
    "Date: {date} Time: {time}.",
    "{date}, {time} -",
    "On dt. {date},",
    "During routine inspection on {date},",
    "While carrying out site round on {date} at {time},",
)

SHIFTS: tuple[str, ...] = ("A", "B", "C", "general", "night", "morning")

ACTION_CLAUSES: tuple[str, ...] = (
    "Job stopped and area barricaded.",
    "Matter reported to Installation Manager.",
    "TBT conducted before resuming the job.",
    "Corrective action taken on the spot.",
    "Deviation closed same day.",
    "Reported in HSE meeting.",
    "Crew counselled by TP.",
    "Observation recorded in daily safety report.",
    "Work resumed after control was put in place.",
    "Contractor supervisor was warned.",
)
