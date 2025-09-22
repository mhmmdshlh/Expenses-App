import argparse
from datetime import datetime
from expense_manager import ExpenseManager
import os
from sync_drive import get_file, upload_file
from tabulate import tabulate
import pandas as pd

DATABASE_NAME = "expenses.db"
BASE_DIR = os.path.dirname(__file__)
data_dir = os.path.join(BASE_DIR, "data")
os.makedirs(data_dir, exist_ok=True)
DATABASE = os.path.join(data_dir, DATABASE_NAME)

def valid_date(s):
    try:
        date_obj = datetime.strptime(s, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        msg = "Invalid date, use 'YYYY-MM-DD' format!"
        raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser(prog="expenses")
sp = parser.add_subparsers(dest="command")

p_add = sp.add_parser("add")
p_add.add_argument("date", type=valid_date)
p_add.add_argument("item")
p_add.add_argument("price", type=int)
p_add.add_argument("category")

p_addmany = sp.add_parser("addmany")
p_addmany.add_argument("--entry", "-e", nargs=4, action="append", metavar=("Date", "Item", "Price", "Category"))
p_addmany.add_argument("--date", help="Set default date for entries (overrides blank Date in each entry)")

p_view = sp.add_parser("view")
p_view.add_argument("-y", "--year", action="extend", nargs='*')
p_view.add_argument("-m", "--month", action="extend", nargs='*')
p_view.add_argument("-d", "--day", action="extend", nargs='*')
p_view.add_argument("--item", action="extend", nargs='+')
p_view.add_argument("--price", action="extend", nargs='+') 
p_view.add_argument("--category_name", action="extend", nargs='+')
p_view.add_argument("--orderby", choices=['id', 'item', 'price', 'date', 'category_name'], default='id')
p_view.add_argument("--limit", type=int, default=None)
p_view.add_argument("--offset", type=int, default=None)
p_view.add_argument('--desc', '--descending', action="store_true")

p_summary = sp.add_parser("summary")
p_summary.add_argument("-gb","--group-by", type=str, default="category", choices=['category', "year", "month", "day"])
p_summary.add_argument("-p","--period", type=str, default="all", choices=['all', 'today', 'this_week', 'this_month', 'this_year'])

p_upcategory = sp.add_parser("upcatname")
p_upcategory.add_argument("oldname")
p_upcategory.add_argument("newname")

p_del = sp.add_parser("delete", aliases=['del', 'd'])
p_del.add_argument("id", type=int)

p_delmany = sp.add_parser("delmany", aliases=['dm'])
p_delmany.add_argument('id', type=int, nargs="+")

p_drive = sp.add_parser("drive")
p_drive.add_argument("opt", choices=["load", "save"])

p_clear = sp.add_parser("clear")

args = parser.parse_args()

db = ExpenseManager(DATABASE)

if args.command == "add":
    if db.add(args.date, args.item, args.price, args.category):
        print(f"Successfully added '{args.item}' to the database.")

elif args.command == "addmany":
    try:
        for date, item, price, cat in args.entry:
            if date == '0' or date == 'x': date = args.date
            date = valid_date(date)
            price = int(price)
            if db.add(date, item, price, cat):
                print(f"Successfully added '{item}' to the database.")
    except (ValueError, argparse.ArgumentTypeError) as e:
        print("Error: ", e)

elif args.command == "view":
    view_filters = {
        'year': args.year,
        'month': args.month,
        'day': args.day,
        'item': args.item,
        'price': args.price,
        'category_name': args.category_name
    }
    
    if view_filters['year'] == []: view_filters['year'].append(datetime.now().strftime('%Y'))
    if view_filters['month'] == []: view_filters['month'].append(datetime.now().strftime('%m'))
    if view_filters['day'] == []: view_filters['day'].append(datetime.now().strftime('%d'))

    if all(x is None for x in view_filters.values()):
        df = db.fetch(orderby=args.orderby, desc=args.desc, limit=args.limit, offset=args.offset)
    else:
        df = db.fetch(filters=view_filters, orderby=args.orderby, desc=args.desc, limit=args.limit, offset=args.offset)
    
    if not df.empty and 'price' in df.columns:
        df['price'] = df['price'].apply(lambda x: f"{x:,}")
         
    headers = [x.capitalize() for x in df.keys()]
    print(tabulate(df, headers=headers, showindex=False, tablefmt='rounded_outline'))

elif args.command == "summary":
    summary_df = db.fetch_summary(group_by=args.group_by, period=args.period)
    if summary_df.empty:
        print("No data available for the specified period.")
    else:
        # Format currency columns for better readability
        price_cols = ['total_amount', 'average_amount', 'min_amount', 'max_amount']
        for col in price_cols:
            if col in summary_df.columns:
                summary_df[col] = summary_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else 'N/A')

        headers = [x.capitalize() for x in summary_df.keys()]
        print(tabulate(summary_df, headers=headers, showindex=False, tablefmt='rounded_outline'))

elif args.command == "upcatname":
    if db.update_category_name(args.oldname, args.newname):
        print(f"Category '{args.oldname}' updated to '{args.newname}'.")

elif args.command in ["delete", "del", 'd']:
    if db.delete_data(args.id):
        print(f"Record with ID {args.id} has been deleted.")

elif args.command in ['delmany', 'dm']:
    for id in args.id:
        if db.delete_data(id):
            print(f"Record with ID {id} has been deleted.")

elif args.command == "drive":
    if args.opt == "load": get_file(DATABASE_NAME, DATABASE)
    elif args.opt == "save": upload_file(DATABASE_NAME, DATABASE)

elif args.command == "clear":
    cur = db.conn.cursor()
    cur.execute("DELETE FROM expenses;")
    cur.execute("DELETE FROM category;")
    db.conn.commit()

db.close()
