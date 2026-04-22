CREATE TABLE IF NOT EXISTS "reading_sessions" (
    "RsID" INTEGER NOT NULL,
    "RsLgID" INTEGER NOT NULL,
    "RsBkID" INTEGER NULL,
    "RsTxID" INTEGER NULL,
    "RsStartedAt" DATETIME NOT NULL,
    "RsEndedAt" DATETIME NULL,
    "RsSource" VARCHAR(20) NOT NULL DEFAULT 'mark_read',
    "RsWordsRead" INTEGER NOT NULL DEFAULT 0,
    "RsPagesRead" INTEGER NOT NULL DEFAULT 0,
    "RsDurationSeconds" INTEGER NULL,
    "RsCreatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("RsID"),
    FOREIGN KEY("RsLgID") REFERENCES "languages" ("LgID") ON UPDATE NO ACTION ON DELETE CASCADE,
    FOREIGN KEY("RsBkID") REFERENCES "books" ("BkID") ON DELETE SET NULL,
    FOREIGN KEY("RsTxID") REFERENCES "texts" ("TxID") ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS "RsLgIDRsStartedAt" ON "reading_sessions" ("RsLgID", "RsStartedAt");
CREATE INDEX IF NOT EXISTS "RsBkIDRsStartedAt" ON "reading_sessions" ("RsBkID", "RsStartedAt");
CREATE INDEX IF NOT EXISTS "RsTxID" ON "reading_sessions" ("RsTxID");

CREATE TABLE IF NOT EXISTS "goals" (
    "GlID" INTEGER NOT NULL,
    "GlScopeType" VARCHAR(20) NOT NULL DEFAULT 'global',
    "GlScopeID" INTEGER NULL,
    "GlMetric" VARCHAR(30) NOT NULL,
    "GlCadence" VARCHAR(20) NOT NULL DEFAULT 'all_time',
    "GlTargetValue" INTEGER NOT NULL,
    "GlStartDate" DATE NOT NULL,
    "GlEndDate" DATE NULL,
    "GlIsActive" TINYINT NOT NULL DEFAULT 1,
    "GlTitle" VARCHAR(120) NOT NULL,
    "GlCreatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("GlID")
);

CREATE INDEX IF NOT EXISTS "GlIsActiveMetricCadence" ON "goals" ("GlIsActive", "GlMetric", "GlCadence");
CREATE INDEX IF NOT EXISTS "GlScopeTypeScopeID" ON "goals" ("GlScopeType", "GlScopeID");

CREATE TABLE IF NOT EXISTS "milestones" (
    "MsID" INTEGER NOT NULL,
    "MsGoalID" INTEGER NULL,
    "MsMetric" VARCHAR(30) NOT NULL,
    "MsThresholdValue" INTEGER NOT NULL,
    "MsTitle" VARCHAR(120) NOT NULL,
    "MsDescription" TEXT NULL,
    "MsReachedAt" DATETIME NULL,
    "MsDisplayOrder" INTEGER NOT NULL DEFAULT 0,
    "MsCreatedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("MsID"),
    FOREIGN KEY("MsGoalID") REFERENCES "goals" ("GlID") ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "MsGoalIDThreshold" ON "milestones" ("MsGoalID", "MsThresholdValue");
CREATE INDEX IF NOT EXISTS "MsMetricReachedAt" ON "milestones" ("MsMetric", "MsReachedAt");

INSERT INTO reading_sessions (
    RsLgID,
    RsBkID,
    RsTxID,
    RsStartedAt,
    RsEndedAt,
    RsSource,
    RsWordsRead,
    RsPagesRead
)
SELECT
    wr.WrLgID,
    tx.TxBkID,
    wr.WrTxID,
    wr.WrReadDate,
    wr.WrReadDate,
    'legacy_backfill',
    wr.WrWordCount,
    CASE WHEN wr.WrTxID IS NULL THEN 0 ELSE 1 END
FROM wordsread wr
LEFT JOIN texts tx ON tx.TxID = wr.WrTxID
WHERE NOT EXISTS (
    SELECT 1 FROM reading_sessions rs
    WHERE rs.RsSource = 'legacy_backfill'
);
