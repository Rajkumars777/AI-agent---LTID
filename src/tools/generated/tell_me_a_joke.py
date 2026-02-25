"""
Auto-generated tool: tell_me_a_joke
"""

import random

def tell_me_a_joke():
    jokes = {
        "animal": [
            "Why did the cat join a band? Because it wanted to be the purr-cussionist!",
            "What do you call a group of cows playing instruments? A moo-sical band!",
            "Why did the elephant quit the circus? Because it was tired of working for peanuts!"
        ],
        "science": [
            "Why did the astronaut break up with his girlfriend? Because he needed space!",
            "Why did the physicist break up with his girlfriend? Because he found her mass attractive, but her charge was always negative!",
            "Why did the chemist quit his job? Because he lost his bond with the company!"
        ],
        "general": [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "Why did the tomato turn red? Because it saw the salad dressing!"
        ]
    }

    joke_topics = ["animal", "science", "general"]
    topic = random.choice(joke_topics)

    return f"[Success] Here's a joke for you: Why {random.choice(jokes[topic])}"

def execute(params: dict) -> str:
    if "topic" in params:
        return tell_me_a_joke()
    else:
        return "[Error] Please specify a topic for the joke."