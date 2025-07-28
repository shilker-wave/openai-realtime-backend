from agents import function_tool
from agents.realtime import RealtimeAgent
from datetime import datetime


@function_tool
def get_current_time() -> str:
    """Gibt das aktuelle Datum und die Uhrzeit zurück."""
    return datetime.now().strftime("%Y-%m-%d %H:%M-%S")


@function_tool
def get_password() -> str:
    """Gibt das Passwort zurück, wenn der Benutzer danach fragt."""
    return "Password1"


informatik: RealtimeAgent = RealtimeAgent(
    name="Fachinformatikdozent",
    instructions="""
        Du bist ein Ausbilder in der Fachinformatik, für Systemintegration und Anwendungsentwicklung.
        Beantworte alle Fragen, die Informatik, Software, Hardware und Programmieren betreffen.
    """,
    handoff_description="Experte für Informatik, Programmierung und Softwareentwicklung",
)


wirtschaft: RealtimeAgent = RealtimeAgent(
    name="Wirtschaftsdozent",
    instructions="""
        Du bist Ausbilder für Wirtschaftsthemen.
        Beantworte alle Fragen, die Wirtschafts- und Handelsthemen betreffen.
    """,
    handoff_description="Experte für Wirtschaft und Handel",
)


leitdozent: RealtimeAgent = RealtimeAgent(
    name="Leitdozent",
    instructions="""
        Du bist ein Leitdozent bei Wave Campus.
        Spreche schnell. Benutze Füllwörter wie 'hmmm', 'ääh' und 'tja'.
        Bei Fragen zu Themen der Informatik, leite an den 'Fachinformatikdozent' weiter.
        Bei Fragen zu Themen der Wirtschaft, leite an den 'Wirtschaftsdozent' weiter
        Ansonsten antworte auf alle anderen Fragen.
    """,
    tools=[
        get_current_time,
        get_password,
    ],
    handoffs=[informatik, wirtschaft],
)