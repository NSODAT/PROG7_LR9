from database import SessionLocal, BookDB

def init_database():
    """Инициализация базы данных начальными данными"""
    db = SessionLocal()

    # Проверяем, есть ли уже данные в базе
    if db.query(BookDB).count() > 0:
        print("База данных уже содержит данные, инициализация не требуется.")
        db.close()
        return

    # Начальные данные
    initial_books = [
        {
            "title": "Война и мир",
            "author": "Лев Толстой",
            "year": 1869,
            "isbn": "9785170987654"
        },
        {
            "title": "Преступление и наказание",
            "author": "Федор Достоевский",
            "year": 1866,
            "isbn": "9785170876543"
        },
        {
            "title": "Евгений Онегин",
            "author": "Александр Пушкин",
            "year": 1833,
            "isbn": "9785170765432"
        }
    ]

    # Добавляем книги в базу данных
    for book_data in initial_books:
        book = BookDB(**book_data)
        db.add(book)

    db.commit()
    print(f"Добавлено {len(initial_books)} книг в базу данных.")

    # Выводим список добавленных книг
    books = db.query(BookDB).all()
    print("\nСписок книг в базе данных:")
    for book in books:
        print(f"ID: {book.id}, Название: {book.title}, Автор: {book.author}, Год: {book.year}")

    db.close()

if __name__ == "__main__":
    init_database()
