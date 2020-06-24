import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    """Inserts (isbn, title, author, year) from books.csv into the table called bookdetails"""
    
    bookFile = open("books.csv")
    bookReader = csv.reader(bookFile)
    #skips the header
    next(bookReader)
    count = 0
    for i, t, a, y in bookReader:
        db.execute("INSERT INTO bookdetails (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                   {"isbn": i, "title": t, "author":a, "year": y})
        count += 1
        if (count % 100) == 0:
            print(f"Added {count} book details to the database")

    print(f"Added {count} book details to the database")
    db.commit()
    bookFile.close()

if __name__ == "__main__":
    main()

