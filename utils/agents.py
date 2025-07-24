from agents import function_tool
from agents.realtime import RealtimeAgent

@function_tool
def get_weather(city: str) -> str:
    """Gibt das Wetter für eine Stadt zurück, wenn der Benutzer danach fragt."""
    return f"Das Wetter in {city} ist sonnig."


@function_tool
def get_secret_number() -> int:
    """Gibt die geheime Zahl zurück, wenn der Benutzer danach fragt."""
    return 42


programming_agent: RealtimeAgent = RealtimeAgent(
    name="Programming Agent",
    instructions=(
        "Du bist ein Experte aller Programmiersprachen."
        "Beantworte alle Fragen zu Programmierung, Code und Softwareentwicklung."
    ),
    handoff_description="Experte für Programmierung und Softwareentwicklung",
)


haiku_agent: RealtimeAgent = RealtimeAgent(
    name="Haiku Agent",
    instructions=(
        "Du bist ein Haiku-Dichter."
        "Du darfst NUR in traditioneller Haikuform (5-7-5 Silben) antworten."
        "Jede Antwort muss ein Haiku sein."
        "Bleibe immer in dieser Form."
    ),
    handoff_description="Erstellt ein Haiku zu einem beliebigen Thema",
)


agent: RealtimeAgent = RealtimeAgent(
    name="Assistant",
    instructions=(
        "Du bist ein Dozent im IT-Bereich."
        "Wenn der Benutzer Poesie oder Haikus anfordert, leite an den Haiku-Agenten weiter."
        "Bei Fragen zu Programmierthemen, leite an den 'Programming Agent' weiter."
        "Ansonsten antworte auf alle anderen Fragen."
    ),
    tools=[
        get_weather,
        get_secret_number,
    ],
    handoffs=[programming_agent, haiku_agent],
)