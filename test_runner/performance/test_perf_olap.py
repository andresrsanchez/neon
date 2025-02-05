from dataclasses import dataclass
from typing import Dict, Tuple

import pytest
from fixtures.compare_fixtures import RemoteCompare
from fixtures.log_helper import log


@dataclass
class LabelledQuery:
    """An SQL query with a label for the test report."""

    label: str
    query: str


# A list of queries to run.
# Please do not alter the label for the query, as it is used to identify it.
# Labels for ClickBench queries match the labels in ClickBench reports
# on https://benchmark.clickhouse.com/ (the DB size may differ).
QUERIES: Tuple[LabelledQuery, ...] = (
    # Disable `black` formatting for the list of queries so that it's easier to read
    # fmt: off
    ### ClickBench queries:
    LabelledQuery("Q0",  r"SELECT COUNT(*) FROM hits;"),
    LabelledQuery("Q1",  r"SELECT COUNT(*) FROM hits WHERE AdvEngineID <> 0;"),
    LabelledQuery("Q2",  r"SELECT SUM(AdvEngineID), COUNT(*), AVG(ResolutionWidth) FROM hits;"),
    LabelledQuery("Q3",  r"SELECT AVG(UserID) FROM hits;"),
    LabelledQuery("Q4",  r"SELECT COUNT(DISTINCT UserID) FROM hits;"),
    LabelledQuery("Q5",  r"SELECT COUNT(DISTINCT SearchPhrase) FROM hits;"),
    LabelledQuery("Q6",  r"SELECT MIN(EventDate), MAX(EventDate) FROM hits;"),
    LabelledQuery("Q7",  r"SELECT AdvEngineID, COUNT(*) FROM hits WHERE AdvEngineID <> 0 GROUP BY AdvEngineID ORDER BY COUNT(*) DESC;"),
    LabelledQuery("Q8",  r"SELECT RegionID, COUNT(DISTINCT UserID) AS u FROM hits GROUP BY RegionID ORDER BY u DESC LIMIT 10;"),
    LabelledQuery("Q9",  r"SELECT RegionID, SUM(AdvEngineID), COUNT(*) AS c, AVG(ResolutionWidth), COUNT(DISTINCT UserID) FROM hits GROUP BY RegionID ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q10", r"SELECT MobilePhoneModel, COUNT(DISTINCT UserID) AS u FROM hits WHERE MobilePhoneModel <> '' GROUP BY MobilePhoneModel ORDER BY u DESC LIMIT 10;"),
    LabelledQuery("Q11", r"SELECT MobilePhone, MobilePhoneModel, COUNT(DISTINCT UserID) AS u FROM hits WHERE MobilePhoneModel <> '' GROUP BY MobilePhone, MobilePhoneModel ORDER BY u DESC LIMIT 10;"),
    LabelledQuery("Q12", r"SELECT SearchPhrase, COUNT(*) AS c FROM hits WHERE SearchPhrase <> '' GROUP BY SearchPhrase ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q13", r"SELECT SearchPhrase, COUNT(DISTINCT UserID) AS u FROM hits WHERE SearchPhrase <> '' GROUP BY SearchPhrase ORDER BY u DESC LIMIT 10;"),
    LabelledQuery("Q14", r"SELECT SearchEngineID, SearchPhrase, COUNT(*) AS c FROM hits WHERE SearchPhrase <> '' GROUP BY SearchEngineID, SearchPhrase ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q15", r"SELECT UserID, COUNT(*) FROM hits GROUP BY UserID ORDER BY COUNT(*) DESC LIMIT 10;"),
    LabelledQuery("Q16", r"SELECT UserID, SearchPhrase, COUNT(*) FROM hits GROUP BY UserID, SearchPhrase ORDER BY COUNT(*) DESC LIMIT 10;"),
    LabelledQuery("Q17", r"SELECT UserID, SearchPhrase, COUNT(*) FROM hits GROUP BY UserID, SearchPhrase LIMIT 10;"),
    LabelledQuery("Q18", r"SELECT UserID, extract(minute FROM EventTime) AS m, SearchPhrase, COUNT(*) FROM hits GROUP BY UserID, m, SearchPhrase ORDER BY COUNT(*) DESC LIMIT 10;"),
    LabelledQuery("Q19", r"SELECT UserID FROM hits WHERE UserID = 435090932899640449;"),
    LabelledQuery("Q20", r"SELECT COUNT(*) FROM hits WHERE URL LIKE '%google%';"),
    LabelledQuery("Q21", r"SELECT SearchPhrase, MIN(URL), COUNT(*) AS c FROM hits WHERE URL LIKE '%google%' AND SearchPhrase <> '' GROUP BY SearchPhrase ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q22", r"SELECT SearchPhrase, MIN(URL), MIN(Title), COUNT(*) AS c, COUNT(DISTINCT UserID) FROM hits WHERE Title LIKE '%Google%' AND URL NOT LIKE '%.google.%' AND SearchPhrase <> '' GROUP BY SearchPhrase ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q23", r"SELECT * FROM hits WHERE URL LIKE '%google%' ORDER BY EventTime LIMIT 10;"),
    LabelledQuery("Q24", r"SELECT SearchPhrase FROM hits WHERE SearchPhrase <> '' ORDER BY EventTime LIMIT 10;"),
    LabelledQuery("Q25", r"SELECT SearchPhrase FROM hits WHERE SearchPhrase <> '' ORDER BY SearchPhrase LIMIT 10;"),
    LabelledQuery("Q26", r"SELECT SearchPhrase FROM hits WHERE SearchPhrase <> '' ORDER BY EventTime, SearchPhrase LIMIT 10;"),
    LabelledQuery("Q27", r"SELECT CounterID, AVG(length(URL)) AS l, COUNT(*) AS c FROM hits WHERE URL <> '' GROUP BY CounterID HAVING COUNT(*) > 100000 ORDER BY l DESC LIMIT 25;"),
    LabelledQuery("Q28", r"SELECT REGEXP_REPLACE(Referer, '^https?://(?:www\.)?([^/]+)/.*$', '\1') AS k, AVG(length(Referer)) AS l, COUNT(*) AS c, MIN(Referer) FROM hits WHERE Referer <> '' GROUP BY k HAVING COUNT(*) > 100000 ORDER BY l DESC LIMIT 25;"),
    LabelledQuery("Q29", r"SELECT SUM(ResolutionWidth), SUM(ResolutionWidth + 1), SUM(ResolutionWidth + 2), SUM(ResolutionWidth + 3), SUM(ResolutionWidth + 4), SUM(ResolutionWidth + 5), SUM(ResolutionWidth + 6), SUM(ResolutionWidth + 7), SUM(ResolutionWidth + 8), SUM(ResolutionWidth + 9), SUM(ResolutionWidth + 10), SUM(ResolutionWidth + 11), SUM(ResolutionWidth + 12), SUM(ResolutionWidth + 13), SUM(ResolutionWidth + 14), SUM(ResolutionWidth + 15), SUM(ResolutionWidth + 16), SUM(ResolutionWidth + 17), SUM(ResolutionWidth + 18), SUM(ResolutionWidth + 19), SUM(ResolutionWidth + 20), SUM(ResolutionWidth + 21), SUM(ResolutionWidth + 22), SUM(ResolutionWidth + 23), SUM(ResolutionWidth + 24), SUM(ResolutionWidth + 25), SUM(ResolutionWidth + 26), SUM(ResolutionWidth + 27), SUM(ResolutionWidth + 28), SUM(ResolutionWidth + 29), SUM(ResolutionWidth + 30), SUM(ResolutionWidth + 31), SUM(ResolutionWidth + 32), SUM(ResolutionWidth + 33), SUM(ResolutionWidth + 34), SUM(ResolutionWidth + 35), SUM(ResolutionWidth + 36), SUM(ResolutionWidth + 37), SUM(ResolutionWidth + 38), SUM(ResolutionWidth + 39), SUM(ResolutionWidth + 40), SUM(ResolutionWidth + 41), SUM(ResolutionWidth + 42), SUM(ResolutionWidth + 43), SUM(ResolutionWidth + 44), SUM(ResolutionWidth + 45), SUM(ResolutionWidth + 46), SUM(ResolutionWidth + 47), SUM(ResolutionWidth + 48), SUM(ResolutionWidth + 49), SUM(ResolutionWidth + 50), SUM(ResolutionWidth + 51), SUM(ResolutionWidth + 52), SUM(ResolutionWidth + 53), SUM(ResolutionWidth + 54), SUM(ResolutionWidth + 55), SUM(ResolutionWidth + 56), SUM(ResolutionWidth + 57), SUM(ResolutionWidth + 58), SUM(ResolutionWidth + 59), SUM(ResolutionWidth + 60), SUM(ResolutionWidth + 61), SUM(ResolutionWidth + 62), SUM(ResolutionWidth + 63), SUM(ResolutionWidth + 64), SUM(ResolutionWidth + 65), SUM(ResolutionWidth + 66), SUM(ResolutionWidth + 67), SUM(ResolutionWidth + 68), SUM(ResolutionWidth + 69), SUM(ResolutionWidth + 70), SUM(ResolutionWidth + 71), SUM(ResolutionWidth + 72), SUM(ResolutionWidth + 73), SUM(ResolutionWidth + 74), SUM(ResolutionWidth + 75), SUM(ResolutionWidth + 76), SUM(ResolutionWidth + 77), SUM(ResolutionWidth + 78), SUM(ResolutionWidth + 79), SUM(ResolutionWidth + 80), SUM(ResolutionWidth + 81), SUM(ResolutionWidth + 82), SUM(ResolutionWidth + 83), SUM(ResolutionWidth + 84), SUM(ResolutionWidth + 85), SUM(ResolutionWidth + 86), SUM(ResolutionWidth + 87), SUM(ResolutionWidth + 88), SUM(ResolutionWidth + 89) FROM hits;"),
    LabelledQuery("Q30", r"SELECT SearchEngineID, ClientIP, COUNT(*) AS c, SUM(IsRefresh), AVG(ResolutionWidth) FROM hits WHERE SearchPhrase <> '' GROUP BY SearchEngineID, ClientIP ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q31", r"SELECT WatchID, ClientIP, COUNT(*) AS c, SUM(IsRefresh), AVG(ResolutionWidth) FROM hits WHERE SearchPhrase <> '' GROUP BY WatchID, ClientIP ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q32", r"SELECT WatchID, ClientIP, COUNT(*) AS c, SUM(IsRefresh), AVG(ResolutionWidth) FROM hits GROUP BY WatchID, ClientIP ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q33", r"SELECT URL, COUNT(*) AS c FROM hits GROUP BY URL ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q34", r"SELECT 1, URL, COUNT(*) AS c FROM hits GROUP BY 1, URL ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q35", r"SELECT ClientIP, ClientIP - 1, ClientIP - 2, ClientIP - 3, COUNT(*) AS c FROM hits GROUP BY ClientIP, ClientIP - 1, ClientIP - 2, ClientIP - 3 ORDER BY c DESC LIMIT 10;"),
    LabelledQuery("Q36", r"SELECT URL, COUNT(*) AS PageViews FROM hits WHERE CounterID = 62 AND EventDate >= '2013-07-01' AND EventDate <= '2013-07-31' AND DontCountHits = 0 AND IsRefresh = 0 AND URL <> '' GROUP BY URL ORDER BY PageViews DESC LIMIT 10;"),
    LabelledQuery("Q37", r"SELECT Title, COUNT(*) AS PageViews FROM hits WHERE CounterID = 62 AND EventDate >= '2013-07-01' AND EventDate <= '2013-07-31' AND DontCountHits = 0 AND IsRefresh = 0 AND Title <> '' GROUP BY Title ORDER BY PageViews DESC LIMIT 10;"),
    LabelledQuery("Q38", r"SELECT URL, COUNT(*) AS PageViews FROM hits WHERE CounterID = 62 AND EventDate >= '2013-07-01' AND EventDate <= '2013-07-31' AND IsRefresh = 0 AND IsLink <> 0 AND IsDownload = 0 GROUP BY URL ORDER BY PageViews DESC LIMIT 10 OFFSET 1000;"),
    LabelledQuery("Q39", r"SELECT TraficSourceID, SearchEngineID, AdvEngineID, CASE WHEN (SearchEngineID = 0 AND AdvEngineID = 0) THEN Referer ELSE '' END AS Src, URL AS Dst, COUNT(*) AS PageViews FROM hits WHERE CounterID = 62 AND EventDate >= '2013-07-01' AND EventDate <= '2013-07-31' AND IsRefresh = 0 GROUP BY TraficSourceID, SearchEngineID, AdvEngineID, Src, Dst ORDER BY PageViews DESC LIMIT 10 OFFSET 1000;"),
    LabelledQuery("Q40", r"SELECT URLHash, EventDate, COUNT(*) AS PageViews FROM hits WHERE CounterID = 62 AND EventDate >= '2013-07-01' AND EventDate <= '2013-07-31' AND IsRefresh = 0 AND TraficSourceID IN (-1, 6) AND RefererHash = 3594120000172545465 GROUP BY URLHash, EventDate ORDER BY PageViews DESC LIMIT 10 OFFSET 100;"),
    LabelledQuery("Q41", r"SELECT WindowClientWidth, WindowClientHeight, COUNT(*) AS PageViews FROM hits WHERE CounterID = 62 AND EventDate >= '2013-07-01' AND EventDate <= '2013-07-31' AND IsRefresh = 0 AND DontCountHits = 0 AND URLHash = 2868770270353813622 GROUP BY WindowClientWidth, WindowClientHeight ORDER BY PageViews DESC LIMIT 10 OFFSET 10000;"),
    LabelledQuery("Q42", r"SELECT DATE_TRUNC('minute', EventTime) AS M, COUNT(*) AS PageViews FROM hits WHERE CounterID = 62 AND EventDate >= '2013-07-14' AND EventDate <= '2013-07-15' AND IsRefresh = 0 AND DontCountHits = 0 GROUP BY DATE_TRUNC('minute', EventTime) ORDER BY DATE_TRUNC('minute', EventTime) LIMIT 10 OFFSET 1000;"),
    ### Custom Neon queries:
    # I suggest using the NQ prefix (which stands for Neon Query) instead of Q
    # to not intersect with the original ClickBench queries if their list is extended.
    #
    # LabelledQuery("NQ0", r"..."),
    # LabelledQuery("NQ1", r"..."),
    # ...
    # fmt: on
)


def run_psql(env: RemoteCompare, labelled_query: LabelledQuery, times: int) -> None:
    # prepare connstr:
    # - cut out password from connstr to pass it via env
    # - add options to connstr
    password = env.pg.default_options.get("password", None)
    options = f"-cstatement_timeout=0 {env.pg.default_options.get('options', '')}"
    connstr = env.pg.connstr(password=None, options=options)

    environ: Dict[str, str] = {}
    if password is not None:
        environ["PGPASSWORD"] = password

    label, query = labelled_query.label, labelled_query.query

    log.info(f"Running query {label} {times} times")
    for i in range(times):
        run = i + 1
        log.info(f"Run {run}/{times}")
        with env.zenbenchmark.record_duration(f"{label}/{run}"):
            env.pg_bin.run_capture(["psql", connstr, "-c", query], env=environ)


@pytest.mark.parametrize("query", QUERIES)
@pytest.mark.remote_cluster
def test_clickbench(query: LabelledQuery, remote_compare: RemoteCompare):
    """
    An OLAP-style ClickHouse benchmark

    Based on https://github.com/ClickHouse/ClickBench/tree/c00135ca5b6a0d86fedcdbf998fdaa8ed85c1c3b/aurora-postgresql
    The DB prepared manually in advance
    """

    run_psql(remote_compare, query, times=3)
