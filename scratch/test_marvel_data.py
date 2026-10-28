import json

characters = {
    "harry": {
        "name": "Harry Potter",
        "role": "The Intuitive Seeker (POV Lead)",
        "house": "Gryffindor",
        "color": "#FACC15",
        "bg_glow": "rgba(250, 204, 21, 0.25)",
        "avatar": "assets/harry_sticker.jpg",
        "tagline": "Follows instinct · Bound by fierce loyalty · Zero tolerance for dark magic",
        "perception": "Sees the world through gut feelings and strong moral absolutes. Quick to defend friends, quick to suspect institutional authority.",
        "active_belief": "100% convinced Severus Snape wants the Philosopher's Stone. Witnessed Snape's leg wound and deduced Fluffy was guarding the underground trapdoor.",
        "blind_spot": "Totally deceived by Quirrell's nervous stutter and timidity. Never suspects the timid Defence Against the Dark Arts teacher.",
        "quote": "Snape’s going through that trapdoor tonight. He’s going to steal the Stone for Voldemort, and I have to stop him."
    },
    "hermione": {
        "name": "Hermione Granger",
        "role": "The Analytical Archivist",
        "house": "Gryffindor",
        "color": "#60A5FA",
        "bg_glow": "rgba(96, 165, 250, 0.25)",
        "avatar": "assets/hermione_sticker.jpg",
        "tagline": "Cataloger of canon · Spell tactician · Logic-driven problem solver",
        "perception": "Interprets reality strictly through books, rules, and verifiable documentation. Trusts published history and institutional procedures.",
        "active_belief": "Deduced Flamel from Chocolate Frog cards; solved Snape's 7-potion logic puzzle; set Snape's cloak on fire because eye-contact is required for cursing.",
        "blind_spot": "Confused correlation with causation—assumed eye-contact equaled cursing, accidentally knocking over Quirrell without realizing he was the true caster.",
        "quote": "Books! And cleverness! There are more important things—friendship and bravery—and Harry, just be careful!"
    },
    "ron": {
        "name": "Ron Weasley",
        "role": "The Strategic Tactician",
        "house": "Gryffindor",
        "color": "#FB923C",
        "bg_glow": "rgba(251, 146, 60, 0.25)",
        "avatar": "assets/ron_sticker.jpg",
        "tagline": "Wizarding instincts · Grandmaster tactician · Unwavering loyalty",
        "perception": "Grounded in wizarding culture and ancient family lore. Inherently suspicious of dark families and Slytherin house politics.",
        "active_belief": "Sacrificed his piece on McGonagall's giant chessboard to secure Harry's checkmate. Believes Snape's bitterness towards Gryffindor proves his malice.",
        "blind_spot": "Underestimates quiet or nervous peers; completely overlooks Quirrell as an inconsequential background teacher.",
        "quote": "Do you want to stop Snape getting that Stone or not? Harry, you’ve got to go on—not me, not Hermione, YOU!"
    },
    "quirrell": {
        "name": "Quirinus Quirrell",
        "role": "The Deceptive Host",
        "house": "Ravenclaw",
        "color": "#C084FC",
        "bg_glow": "rgba(192, 132, 252, 0.25)",
        "avatar": "assets/quirrell_sticker.jpg",
        "tagline": "Master of feigned weakness · Dark conduit · Voldemort's vessel",
        "perception": "Cold, calculated, fully subservient to Voldemort's whisper. Uses perceived patheticness as an impenetrable cognitive camouflage.",
        "active_belief": "Let the troll in on Halloween; jinxed Harry's Nimbus 2000; slaughtered unicorns in the forest; actively manipulating the Mirror of Erised.",
        "blind_spot": "Cannot fathom selfless love or sacrifice; baffled by how Harry pulled the Stone from the Mirror without desiring to use it.",
        "quote": "Severus does seem the type, doesn’t he? Next to him, who would suspect p-p-poor, st-stuttering Professor Quirrell?"
    },
    "snape": {
        "name": "Severus Snape",
        "role": "The Misunderstood Guardian",
        "house": "Slytherin",
        "color": "#4ADE80",
        "bg_glow": "rgba(74, 222, 128, 0.25)",
        "avatar": "assets/snape_sticker.jpg",
        "tagline": "Unwavering secret oath · Occlumency master · Shadow protector",
        "perception": "Bitter, hyper-vigilant, trapped between an eternal oath to Lily Potter and a ruthless exterior required to maintain cover.",
        "active_belief": "Counter-jinxed Quirrell at the match; threatened Quirrell in the forest; intercepted the trapdoor on Halloween and took Fluffy's bite.",
        "blind_spot": "Inability to show empathy or warmth ensures Harry misinterprets every single life-saving protective action as attempted murder.",
        "quote": "You don’t want me as your enemy, Quirrell. We’ll have another little chat soon, when you’ve had time to decide where your loyalties lie."
    }
}
print(f"Total characters: {len(characters)}")
