import sqlite3
import pandas as pd
from datetime import datetime

class ExpenseManager:
    """Manages expense records in SQLite database."""

    # --- Nested Exception Classes ---
    class Error(Exception):
        """Base exception for all ExpenseManager errors."""
        pass

    class DatabaseConnectionError(Error):
        """Raised when database connection fails."""
        pass

    class DatabaseOperationError(Error):
        """Raised when database operation fails."""
        pass

    class InvalidInputError(Error):
        """Raised when input validation fails."""
        pass
    
    CREATE_CATEGORY_TABLE = '''CREATE TABLE IF NOT EXISTS category (
        id INTEGER PRIMARY KEY,
        category_name TEXT UNIQUE
    );'''
    
    CREATE_EXPENSES_TABLE = '''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY,
        date TEXT NOT NULL,
        item TEXT NOT NULL,
        price INTEGER CHECK (price >= 0),
        category_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES category (id)
    );'''

    def __init__(self, db: str):
        """Initialize database connection.
        
        Args:
            db: Path to SQLite database file
            
        Raises:
            DatabaseConnectionError: If connection to database fails
        """
        self.db = db
        try:
            self.conn = sqlite3.connect(self.db)
            self.create_tables()
        except sqlite3.Error as e:
            raise self.DatabaseConnectionError(f"Failed to connect to database: {e}")
    
    def __enter__(self):
        self.conn = sqlite3.connect(self.db)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        """Create the database tables if they don't exist yet."""
        stats = [
            self.CREATE_CATEGORY_TABLE,
            self.CREATE_EXPENSES_TABLE,
            'CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);',
            'CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);',
            "PRAGMA foreign_keys = ON;"
        ]
        cur = self.conn.cursor()
        for stat in stats:
            cur.execute(stat)
        self.conn.commit()

    def add(self, date: str, item: str, price: int, cat: str) -> bool:
        """Add a new expense record to the database.
        
        Args:
            date: Date of the expense in YYYY-MM-DD format
            item: Name of the expense item
            price: Price of the item
            cat: Category of the expense
            
        Returns:
            bool: True if the record was added successfully
            
        Raises:
            InvalidInputError: If input validation fails
            DatabaseOperationError: If database operation fails
        """
        # Input validation
        if not all([date, item, cat]):
            raise self.InvalidInputError("Date, item, and category cannot be empty")
        if price < 0:
            raise self.InvalidInputError("Price cannot be negative")
            
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        except ValueError as e:
            raise self.InvalidInputError(f"Invalid date format. Use YYYY-MM-DD: {e}")

        try:
            cur = self.conn.cursor()
            
            # Normalize category name by removing leading/trailing whitespace
            normalized_cat = cat.strip()
            
            # Add category if not exists
            cur.execute("INSERT OR IGNORE INTO category (category_name) VALUES (?);", (normalized_cat,))
            cur.execute("SELECT id FROM category WHERE category_name = ?;", (normalized_cat,))
            cat_id = cur.fetchone()
            
            if not cat_id:
                raise self.DatabaseOperationError("Failed to get or create category")
            
            cat_id = cat_id[0]

            # Add expense
            cur.execute(
                "INSERT INTO expenses (date, item, price, category_id) VALUES (?,?,?,?);",
                (date_obj.strftime("%Y-%m-%d"), item, price, cat_id)
            )
            self.conn.commit()
            return True
            
        except sqlite3.Error as e:
            self.conn.rollback()
            raise self.DatabaseOperationError(f"Failed to add expense: {e}")

    def fetch(self, filters:dict = None, orderby='id', desc=False, limit=None, offset=None) -> pd.DataFrame:
        """Fetch expense records from the database.
        
        Args:
            filters: Dictionary of filter conditions
            orderby: Column name to order by
            desc: Boolean indicating descending order
            limit : Maximum number of records to fetch
            offset: Number of records to skip
            
        Returns:
            Pandas DataFrame containing the fetched records.
        """
        allowed_orderby = ['id', 'date', 'item', 'price', 'category_name']
        if orderby not in allowed_orderby:
            orderby = 'id'
            
        stat = "SELECT expenses.id id, date, item, price, category_name FROM expenses JOIN category ON expenses.category_id = category.id"
        params = []
        if filters:
            allowed_keys = ['id', 'year', 'month', 'day', 'item', 'price', 'category_name']
            where_clauses = []
            for key, values in filters.items():
                if key in allowed_keys and values:
                    if key == 'year':
                        query = ["strftime('%Y', date) = ?" for _ in values]
                        where_clauses.append('(' + ' OR '.join(query) + ')')
                        params.extend(values)
                    elif key == 'month':
                        query = ["strftime('%m', date) = ?" for _ in values]
                        where_clauses.append('(' + ' OR '.join(query) + ')')
                        values = [x.zfill(2) for x in values]
                        params.extend(values)
                    elif key == 'day':
                        query = ["strftime('%d', date) = ?" for _ in values]
                        where_clauses.append('(' + ' OR '.join(query) + ')')
                        values = [x.zfill(2) for x in values]
                        params.extend(values)
                    elif key == 'category_name':
                        normalized_values = [v.strip() for v in values]
                        query = [f"{key} = ?" for _ in normalized_values]
                        where_clauses.append('(' + ' OR '.join(query) + ')')
                        params.extend(normalized_values)
                    elif key == 'id':
                        query = [f"expenses.{key} = ?" for _ in values]
                        where_clauses.append('(' + ' OR '.join(query) + ')')
                        params.extend(values)
                
            if where_clauses:
                stat += ' WHERE ' + ' AND '.join(where_clauses)

        stat += f' ORDER BY {orderby} {"DESC" if desc else "ASC"}'

        if limit:
            stat += f' LIMIT {int(limit)}'
        if offset:
            stat += f' OFFSET {int(offset)}'

        stat += ';'

        df = pd.read_sql_query(stat, self.conn, params=params)
        return df
    
    def update_category_name(self, old_name: str, new_name: str) -> bool:
        """Update an existing category name.
        
        Args:
            old_name: Current name of the category
            new_name: New name for the category
            
        Returns:
            bool: True if the category name was updated
            
        Raises:
            InvalidInputError: If input validation fails
            DatabaseOperationError: If database operation fails
        """
        if not old_name or not new_name:
            raise self.InvalidInputError("Category names cannot be empty")
            
        # Normalize category names
        normalized_old_name = old_name.strip()
        normalized_new_name = new_name.strip()
        
        if not normalized_old_name or not normalized_new_name:
            raise self.InvalidInputError("Category names cannot be just whitespace")
            
        if normalized_old_name == normalized_new_name:
            return True  # No change needed
            
        try:
            cur = self.conn.cursor()
            cur.execute("UPDATE category SET category_name = ? WHERE category_name = ?", 
                       (normalized_new_name, normalized_old_name))
            self.conn.commit()
            
            if cur.rowcount == 0:
                raise self.InvalidInputError(f"Category '{old_name}' not found")
                
            return True
            
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise self.InvalidInputError(f"Category '{new_name}' already exists")
        except sqlite3.Error as e:
            self.conn.rollback()
            raise self.DatabaseOperationError(f"Failed to update category: {e}")

    def delete_data(self, id: int) -> bool:
        """Delete an expense record by its ID.
        
        Args:
            id: ID of the expense record to delete
            
        Returns:
            bool: True if the record was deleted
            
        Raises:
            InvalidInputError: If input validation fails
            DatabaseOperationError: If database operation fails
        """
        if not isinstance(id, int) or id <= 0:
            raise self.InvalidInputError("Invalid expense ID")
            
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM expenses WHERE id = ?;", (id,))
            self.conn.commit()
            
            if cur.rowcount == 0:
                raise self.InvalidInputError(f"Expense with ID {id} not found")
                
            return True
            
        except sqlite3.Error as e:
            self.conn.rollback()
            raise self.DatabaseOperationError(f"Failed to delete expense: {e}")
        
    def close(self):
        """Close the database connection."""
        self.conn.close()
    
    def fetch_summary(self, group_by: str = 'category', period: str = 'this_month') -> pd.DataFrame:
        """
        Fetch expense summary, grouped by a specified column and filtered by a time period.
        
        Args:
            group_by (str): Column to group by. Allowed: 'category', 'year', 'month', 'day'.
            period (str): Time period to filters by. Allowed: 'all', 'today', 'this_week', 'this_month', 'this_year'.
        
        Returns:
            pd.DataFrame: DataFrame with summary statistics.
            
        Raises:
            InvalidInputError: If group_by or period values are not allowed.
            DatabaseOperationError: If the database query fails.
        """
        # 1. Validate inputs
        allowed_group_by = ['category', 'year', 'month', 'day']
        if group_by not in allowed_group_by:
            raise self.InvalidInputError(f"Invalid group_by value. Allowed: {allowed_group_by}")

        allowed_periods = ['all', 'today', 'this_week', 'this_month', 'this_year']
        if period not in allowed_periods:
            raise self.InvalidInputError(f"Invalid period value. Allowed: {allowed_periods}")

        # 2. Determine grouping expression from validated input
        group_expression_map = {
            'category': 'category_name',
            'year': "strftime('%Y', date)",
            'month': "strftime('%Y-%m', date)",
            'day': 'date'
        }
        group_col_expression = group_expression_map[group_by]

        # 3. Determine WHERE clause for the time period
        where_clause = ""
        if period == 'today':
            where_clause = "WHERE date = date('now', 'localtime')"
        elif period == 'this_week':
            # SQLite's week starts on Sunday. This captures the current week.
            where_clause = "WHERE strftime('%Y-%W', date) = strftime('%Y-%W', 'now', 'localtime')"
        elif period == 'this_month':
            where_clause = "WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime')"
        elif period == 'this_year':
            where_clause = "WHERE strftime('%Y', date) = strftime('%Y', 'now', 'localtime')"
        # For 'all', where_clause remains empty, fetching all data.

        # 4. Construct the final, safe query
        query = f"""
            SELECT
                {group_col_expression} as summary_group,
                COUNT(*) as transaction_count,
                SUM(price) as total_amount,
                ROUND(AVG(price)) as average_amount,
                MIN(price) as min_amount,
                MAX(price) as max_amount
            FROM expenses
            JOIN category ON expenses.category_id = category.id
            {where_clause}
            GROUP BY 
            summary_group
            ORDER BY summary_group;
        """

        # 5. Execute the query
        try:
            return pd.read_sql_query(query, self.conn)
        except sqlite3.Error as e:
            raise self.DatabaseOperationError(f"Failed to fetch summary: {e}")
    
    @property
    def last_date(self):
        stat = "select date from expenses order by date desc limit 1;"
        cur = self.conn.cursor()
        cur.execute(stat)
        row = cur.fetchone()
        if not row:
            return None
        result = row[0]
        return datetime.strptime(result, "%Y-%m-%d")
