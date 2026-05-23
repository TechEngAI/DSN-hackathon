LANGUAGE_INSTRUCTIONS = {
    "standard": (
        "Write in clear, professional English. "
        "Be descriptive and informative."
    ),
    "naija": (
        "Mix in Nigerian Pidgin naturally throughout your response. "
        "Use phrases like 'e sweet die', 'no dulling', 'my guy', 'confirm', 'abeg', "
        "'no wahala', 'chop life', 'padi'. "
        "Keep it readable but culturally authentic and warm."
    ),
    "pidgin": (
        "Write fully in Nigerian Pidgin English. "
        "Heavy use of local expressions. Use Yoruba, Igbo, and Hausa words mixed in naturally. "
        "Examples: 'e dey hit', 'Oshey!', 'no wahala', 'chop life', 'na so e be', "
        "'Chineke!', 'Kai!', 'e sweet well well', 'abeg no dulling', 'my padi'. "
        "The response should feel like it was written by a real Nigerian on the street."
    )
}


def get_language_instruction(language_mode: str) -> str:
    return LANGUAGE_INSTRUCTIONS.get(language_mode, LANGUAGE_INSTRUCTIONS["naija"])
