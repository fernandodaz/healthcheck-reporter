from __future__ import annotations

import socket


def probe_tcp_connectivity(host: str, port: int, timeout_seconds: float) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        try:
            sock.connect((host, port))
            return True
        except Exception:
            return False


def probe_postgres_connectivity(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    timeout_seconds: float,
) -> bool:
    try:
        import psycopg2  # type: ignore
        from psycopg2 import OperationalError  # type: ignore
    except Exception:
        return False

    dsn: str = (
        f"host={host} port={int(port)} dbname={dbname} user={user} password={password} "
        f"connect_timeout={int(max(1.0, timeout_seconds))}"
    )
    try:
        conn = psycopg2.connect(dsn)
        try:
            conn.close()
        except Exception:
            pass
        return True
    except OperationalError:
        return False
    except Exception:
        return False


