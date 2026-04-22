-- Add BkReadingStatus column to books table
alter table books add column BkReadingStatus VARCHAR(20) DEFAULT 'not_started';

-- Set initial status based on current data
-- If book has pages read, it's 'completed' or 'reading'
UPDATE books
SET BkReadingStatus = CASE
    WHEN BkArchived = 1 THEN 'abandoned'
    WHEN BkCurrentTxID = 0 THEN 'not_started'
    WHEN BkCurrentTxID IN (
        SELECT TxID FROM texts WHERE TxReadDate IS NOT NULL
    ) THEN 'completed'
    ELSE 'reading'
END;
