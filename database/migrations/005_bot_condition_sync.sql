-- Replacing one program version's current condition links preserves their historical source in RAW.
-- This is the only DELETE privilege required by the bot; RAW remains append-only.
GRANT DELETE ON core.program_conditions TO atlas_ingest;
