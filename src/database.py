"""Read-only access to the source tables and explicit local CSV mode."""

from pathlib import Path

import pandas as pd

KEY = ["park_code", "year", "month"]
WEATHER = ["avg_temp_c", "total_precip_mm", "total_snowfall_cm"]
VISITS = "recreation_visits"
COLUMNS = {
    "parks": ["park_code", "park_name", "state", "latitude", "longitude"],
    "visitation": KEY + [VISITS],
    "weather": KEY + WEATHER,
}


def open_readonly(dsn):
    """Create a TLS connection that can only execute a read-only snapshot."""
    import psycopg
    sslmode = psycopg.conninfo.conninfo_to_dict(dsn).get("sslmode", "require")
    connection = psycopg.connect(dsn, connect_timeout=10, sslmode=sslmode)
    connection.read_only = True
    connection.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
    return connection


def read_tables(connection):
    from psycopg import sql
    frames = {}
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout = 30000")
        for table, columns in COLUMNS.items():
            query = sql.SQL("SELECT {} FROM public.{}").format(
                sql.SQL(", ").join(map(sql.Identifier, columns)), sql.Identifier(table)
            )
            cursor.execute(query)
            frames[table] = pd.DataFrame(cursor.fetchall(), columns=columns)
    return frames


def read_postgres(dsn):
    with open_readonly(dsn) as connection:
        return read_tables(connection)


def read_csv_directory(directory):
    return {
        table: pd.read_csv(Path(directory) / f"{table}_supabase.csv", usecols=columns)
        for table, columns in COLUMNS.items()
    }


def prepare(frames):
    """Validate join keys and preserve weather-only and visitation-only months."""
    tables = {}
    invalid_values = 0
    for name, columns in COLUMNS.items():
        df = frames[name][columns].copy()
        df["park_code"] = df["park_code"].astype("string").str.strip().str.upper()
        keys = ["park_code"] if name == "parks" else KEY
        if name != "parks":
            for field in ("year", "month"):
                df[field] = pd.to_numeric(df[field], errors="coerce")
            valid = df["year"].between(1, 9999) & df["month"].between(1, 12)
            valid &= df["year"].mod(1).eq(0) & df["month"].mod(1).eq(0)
            if not valid.all():
                raise ValueError(f"{name} contains invalid year or month keys.")
            df[["year", "month"]] = df[["year", "month"]].astype(int)
        if df["park_code"].isna().any() or df["park_code"].eq("").any():
            raise ValueError(f"{name} contains empty park codes.")
        df = df.drop_duplicates()
        if df.duplicated(keys).any():
            raise ValueError(f"{name} contains conflicting records for the same key.")
        for field in set(columns) - set(keys) - {"park_name", "state"}:
            values = pd.to_numeric(df[field], errors="coerce")
            valid = values.abs().lt(float("inf"))
            if field == "latitude":
                valid &= values.between(-90, 90)
            elif field == "longitude":
                valid &= values.between(-180, 180)
            elif field != "avg_temp_c":
                valid &= values.ge(0)
            invalid_values += int((df[field].notna() & ~valid).sum())
            df[field] = values.where(valid)
        tables[name] = df

    parks = tables["parks"].sort_values("park_name").reset_index(drop=True)
    for field in ("park_name", "state"):
        parks[field] = parks[field].astype("string").str.strip().replace("", pd.NA)
    parks["park_name"] = parks["park_name"].fillna(parks["park_code"])
    parks["state"] = parks["state"].fillna("Unknown")
    history = tables["weather"].merge(tables["visitation"], on=KEY, how="outer",
                                      validate="one_to_one", indicator="source")
    known = history["park_code"].isin(parks["park_code"])
    orphan_rows = int((~known).sum())
    return parks, history.loc[known].copy(), invalid_values, orphan_rows
