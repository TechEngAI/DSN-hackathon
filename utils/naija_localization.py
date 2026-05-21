import os
import json
import re
import random

class NaijaLocalizer:
    def __init__(self, mapping_path: str = None):
        if not mapping_path:
            # Try workspace root and analytics folders
            possible_paths = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cultural_proxy_map.json")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "analytics", "cultural_proxy_map.json")),
                "cultural_proxy_map.json"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    mapping_path = path
                    break

        self.mappings = []
        if mapping_path and os.path.exists(mapping_path):
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.mappings = data.get("mappings", [])
            except Exception as e:
                print(f"Error loading cultural proxy map: {e}")

    def localize_text(self, text: str, lifestyle_profile: str = None) -> str:
        """
        Scans global English keywords in the text and replaces them with their
        Nigerian cultural touchpoints/Pidgin equivalents.
        """
        localized = text
        for mapping in self.mappings:
            keyword = mapping.get("global_keyword", "")
            pidgin_raw = mapping.get("pidgin_equivalent", "")
            if not keyword or not pidgin_raw:
                continue

            # Pick a random option if multiple slash-separated options are present
            pidgin_opts = [opt.strip() for opt in pidgin_raw.split("/") if opt.strip()]
            pidgin = random.choice(pidgin_opts) if pidgin_opts else pidgin_raw

            # Case-insensitive word boundary replacement
            pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
            
            # Simple randomized decision to keep text sounding natural and not overly forced
            if pattern.search(localized) and random.random() > 0.15:
                # Keep capitalizations matching if possible
                def replace_match(match):
                    word = match.group(0)
                    if word.isupper():
                        return pidgin.upper()
                    if word[0].isupper():
                        # Title case pidgin equivalent
                        return " ".join([w.capitalize() for w in pidgin.split()])
                    return pidgin.lower()
                
                localized = pattern.sub(replace_match, localized)

        # Inject lifestyle-specific exclamation or phrases if provided
        if lifestyle_profile:
            slang_injection = self.get_lifestyle_phrases(lifestyle_profile)
            if slang_injection and random.random() > 0.3:
                phrase = random.choice(slang_injection)
                if localized.endswith((".", "!", "?")):
                    localized = localized[:-1] + f", {phrase}!"
                else:
                    localized += f", {phrase}!"

        return localized

    def get_lifestyle_phrases(self, profile: str) -> list[str]:
        """Returns typical Pidgin slang phrases associated with a lifestyle profile."""
        profile_slang = {
            "Beer_Parlour_Regular": [
                "no long thing at all", "joint make sense well-well", "beta parlour to hang out", "lager cold correct"
            ],
            "Detty_December_Vibe": [
                "detty december vibe", "no dulling at all", "turn up correct", "active night life", "standard lifestyle"
            ],
            "Suya_Enthusiast": [
                "pepper go kill person", "spicy meat sweet die", "active pepper touchpoint", "correct suya blend"
            ],
            "Buka_Regular": [
                "food sweet well-well", "correct Buka taste", "Mama Put try well-well", "beta local menu"
            ],
            "Slay_Queen_Vibe": [
                "slay queen standard", "correct beauty vibe", "sweet salon die", "clean body wash correct"
            ],
            "Ajebutter_Executive": [
                "ajebutter standard", "correct soft life", "high-end chill", "no stress at all"
            ],
            "Landlord_Vibe": [
                "oga job well done", "correct fix", "no long delay", "work correct"
            ],
            "Book_and_Chill_Vibe": [
                "calm vibe sweet die", "read and chill correct", "cool space", "no noise at all"
            ],
            "Soft_Life_Chaser": [
                "soft life sweet die", "correct enjoyment", "no stress standard", "everything correct"
            ]
        }
        return profile_slang.get(profile, ["everything correct", "no long thing"])

if __name__ == "__main__":
    localizer = NaijaLocalizer()
    sample_review = "I visited the local pub and the waiter was very fast. However, the meal was expensive and the manager was rude."
    print("Original:", sample_review)
    print("Localized (General):", localizer.localize_text(sample_review))
    print("Localized (Beer Parlour Regular):", localizer.localize_text(sample_review, "Beer_Parlour_Regular"))
