CHARACTER_CONFIG = {
    "harry": {
        "name": "Harry Potter",
        "title": "The Intuitive Seeker",
        "house": "🦁 Gryffindor",
        "accent": "#facc15",
        "accent_glow": "rgba(250, 204, 21, 0.4)",
        "avatar": "assets/characters/harry.webp",
        "tags": ["⚡ The Chosen One", "🧹 Quidditch Seeker", "🦁 Fierce Loyalty", "🩸 Anti-Snape Bias"],
        "stats": [
            {"label": "Gut Intuition", "value": 94, "desc": "Acts on instinct"},
            {"label": "Belief Rigidity", "value": 92, "desc": "Unshakable suspicion"},
            {"label": "Truth Horizon", "value": 35, "desc": "Blind to Quirrell"}
        ],
        "belief": "100% convinced Severus Snape is trying to steal the Stone through Fluffy's trapdoor.",
        "quote": "“Snape’s going through that trapdoor tonight. He’s going to steal the Stone, and I have to stop him.”"
    },
    "hermione": {
        "name": "Hermione Granger",
        "title": "The Analytical Archivist",
        "house": "🦁 Gryffindor",
        "accent": "#60a5fa",
        "accent_glow": "rgba(96, 165, 250, 0.4)",
        "avatar": "assets/characters/hermione.webp",
        "tags": ["📚 Top of the Class", "🧪 Logic Puzzles", "📜 Canon Fact-Checking", "🔥 Cloak Incinerator"],
        "stats": [
            {"label": "Logical Rigor", "value": 98, "desc": "Rules & verifiable facts"},
            {"label": "Belief Rigidity", "value": 86, "desc": "Causal correlation trap"},
            {"label": "Truth Horizon", "value": 45, "desc": "Misjudged eye-contact"}
        ],
        "belief": "Deduced Flamel from Chocolate Frog cards; set Snape's cloak on fire assuming eye-contact meant cursing.",
        "quote": "“Books! And cleverness! There are more important things—friendship and bravery—and Harry, just be careful!”"
    },
    "ron": {
        "name": "Ron Weasley",
        "title": "The Strategic Tactician",
        "house": "🦁 Gryffindor",
        "accent": "#fb923c",
        "accent_glow": "rgba(251, 146, 60, 0.4)",
        "avatar": "assets/characters/ron.webp",
        "tags": ["♟️ Chess Grandmaster", "⚔️ Knight's Sacrifice", "🏰 Wizard Folklore", "🤝 Brotherly Devotion"],
        "stats": [
            {"label": "Tactical Insight", "value": 91, "desc": "Board evaluation"},
            {"label": "Belief Rigidity", "value": 84, "desc": "Deep Slytherin mistrust"},
            {"label": "Truth Horizon", "value": 30, "desc": "Overlooked quiet tutor"}
        ],
        "belief": "Sacrificed his knight on McGonagall's chessboard. Believes Snape's anti-Gryffindor grudge confirms guilt.",
        "quote": "“Do you want to stop Snape getting that Stone or not? Harry, you’ve got to go on—YOU!”"
    },
    "quirrell": {
        "name": "Professor Quirrell",
        "title": "The Deceptive Host",
        "house": "🦅 Ravenclaw / Dark Vessel",
        "accent": "#c084fc",
        "accent_glow": "rgba(192, 132, 252, 0.45)",
        "avatar": "assets/characters/quirrell.webp",
        "tags": ["🎭 Feigned Timidity", "🐍 Voldemort Host", "🧣 Turban Decoy", "🪞 Mirror Manipulator"],
        "stats": [
            {"label": "Deception & Camouflage", "value": 99, "desc": "Stuttering persona"},
            {"label": "Subservience", "value": 96, "desc": "Bound to Dark Lord"},
            {"label": "Conspiracy Awareness", "value": 95, "desc": "Full plot omniscience"}
        ],
        "belief": "Let the troll in on Halloween; jinxed Harry's broom; drinking unicorn blood to sustain his master.",
        "quote": "“Severus does seem the type, doesn’t he? Next to him, who would suspect p-p-poor, st-stuttering Professor Quirrell?”"
    }
}
print("Config loaded successfully:", len(CHARACTER_CONFIG))
