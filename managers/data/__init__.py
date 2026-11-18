"""DataManager: JsonDataManager (flat file) and SqliteDataManager (database, default) with its
FoundItemRowMapper, plus DataManagerFactory (chooses the store) and DataMigrator (JSON -> database).
SqliteDatabase does the file handling and transactions for the database store; SqliteColumnMigrator
adds newer columns to an older found_items table."""
