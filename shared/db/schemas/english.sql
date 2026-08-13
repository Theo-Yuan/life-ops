-- English Learning Database Schema
-- SQLite

CREATE TABLE study_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    activity TEXT NOT NULL,  -- listening / reading / writing / speaking / vocabulary
    detail TEXT,             -- specific task (e.g., "Cambridge 13 Test 1 Section 3")
    notes TEXT
);

CREATE TABLE vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_added TEXT NOT NULL,
    word TEXT NOT NULL UNIQUE,
    meaning TEXT,
    example_sentence TEXT,
    source TEXT,             -- e.g., "cambridge-13-test-1"
    status TEXT DEFAULT 'learning',  -- learning / reviewing / mastered
    last_reviewed TEXT,
    review_count INTEGER DEFAULT 0
);

CREATE TABLE mock_test (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    source TEXT,             -- e.g., "Cambridge 13 Test 1"
    listening_score REAL,
    reading_score REAL,
    writing_score REAL,
    speaking_score REAL,
    overall_score REAL,
    notes TEXT
);

CREATE TABLE daily_goal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    target_min INTEGER DEFAULT 60,
    actual_min INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0  -- boolean
);
