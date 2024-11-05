from pysaic.settings import END_OF_ACTOR_CHARACTER, START_OF_ACTOR_CHARACTER


def escape_stand_and_end(string: str) -> str:
    return string.replace(START_OF_ACTOR_CHARACTER, "|(:").replace(
        END_OF_ACTOR_CHARACTER, ":)|"
    )
