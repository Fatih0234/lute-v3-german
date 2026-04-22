-- Add BkCreated column to books table to track when books were added
alter table books add column BkCreated datetime null;

-- Set creation date for existing books using the earliest text start date
-- For books with no texts, use current timestamp as fallback
UPDATE books
SET BkCreated = (
    SELECT MIN(TxStartDate)
    FROM texts
    WHERE TxBkID = books.BkID
)
WHERE BkID IN (
    SELECT DISTINCT TxBkID
    FROM texts
    WHERE TxStartDate IS NOT NULL
);

-- For books without any text start dates, use current time
UPDATE books
SET BkCreated = datetime('now')
WHERE BkCreated IS NULL;
