from neo4j import Driver, GraphDatabase, NotificationMinimumSeverity
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from pov_retell.config import Settings


class Neo4jUnavailable(RuntimeError):
    """Neo4j cannot be reached or refused the credentials. The message says what to do."""


def connect(settings: Settings) -> Driver:
    """Open a driver from the settings. The password is read here and never printed."""
    password = settings.NEO4J_PASSWORD.get_secret_value()
    if not password:
        raise Neo4jUnavailable(
            "NEO4J_PASSWORD is not set: put it in .env, then run `make neo4j-up`"
        )
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.NEO4J_USER, password),
        notifications_min_severity=NotificationMinimumSeverity.OFF,
    )


def check_health(driver: Driver) -> dict[str, str]:
    """Return the server version and edition, or raise Neo4jUnavailable."""
    try:
        driver.verify_connectivity()
        record, _, _ = driver.execute_query(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition"
        )
    except (ServiceUnavailable, OSError) as exc:
        raise Neo4jUnavailable("cannot reach Neo4j: is it up? run `make neo4j-up`") from exc
    except Neo4jError as exc:
        raise Neo4jUnavailable(f"Neo4j refused the request: {exc.message}") from exc
    return dict(record[0])
