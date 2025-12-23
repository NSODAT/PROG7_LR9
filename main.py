from fastapi import FastAPI, HTTPException, status, Depends, Security
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db, BookDB
from auth import verify_api_key

# Создание приложения FastAPI
app = FastAPI(
    title="Books API",
    description="REST API для управления библиотекой книг",
    version="1.0.0"
)

# Модели Pydantic
class Book(BaseModel):
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200, description="Название книги")
    author: str = Field(..., min_length=1, max_length=100, description="Автор книги")
    year: int = Field(..., ge=1000, le=datetime.now().year, description="Год издания")
    isbn: Optional[str] = Field(None, min_length=10, max_length=13, description="ISBN книги")

class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Название книги")
    author: Optional[str] = Field(None, min_length=1, max_length=100, description="Автор книги")
    year: Optional[int] = Field(None, ge=1000, le=datetime.now().year, description="Год издания")
    isbn: Optional[str] = Field(None, min_length=10, max_length=13, description="ISBN книги")

# GET /api/books - Получение списка всех книг
@app.get("/api/books", response_model=List[Book], tags=["Books"])
async def get_books(
    skip: int = 0,
    limit: int = 10,
    author: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Получить список книг с фильтрацией и пагинацией.
    - **skip**: Количество книг для пропуска (offset)
    - **limit**: Максимальное количество книг в ответе
    - **author**: Фильтр по автору (частичное совпадение)
    - **year_from**: Минимальный год издания
    - **year_to**: Максимальный год издания
    """
    query = db.query(BookDB)
    
    if author:
        query = query.filter(BookDB.author.ilike(f"%{author}%"))
    if year_from:
        query = query.filter(BookDB.year >= year_from)
    if year_to:
        query = query.filter(BookDB.year <= year_to)
    
    books = query.offset(skip).limit(limit).all()
    return books

# GET /api/books/{book_id} - Получение книги по ID
@app.get("/api/books/{book_id}", response_model=Book, tags=["Books"])
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """
    Возвращает информацию о книге с указанным ID.
    Если книга не найдена, возвращается ошибка 404.
    """
    book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if book:
        return book
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Книга с ID {book_id} не найдена"
    )

# POST /api/books - Создание новой книги (требуется аутентификация)
@app.post("/api/books", response_model=Book, status_code=status.HTTP_201_CREATED, tags=["Books"])
async def create_book(book: Book, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db)):
    """
    Создать новую книгу.
    Принимает данные новой книги и добавляет её в систему.
    Автоматически генерирует уникальный ID для книги.
    Возвращает созданную книгу с присвоенным ID.
    """
    db_book = BookDB(**book.model_dump(exclude={"id"}))
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

# PUT /api/books/{book_id} - Полное обновление книги (требуется аутентификация)
@app.put("/api/books/{book_id}", response_model=Book, tags=["Books"])
async def update_book(book_id: int, updated_book: Book, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db)):
    """
    Полностью обновить информацию о книге.
    - **book_id**: ID книги для обновления
    - **updated_book**: Новые данные книги (все поля обязательны)
    Заменяет все данные книги новыми значениями.
    Если книга не найдена, возвращается ошибка 404.
    """
    book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Книга с ID {book_id} не найдена"
        )
    
    for field, value in updated_book.model_dump(exclude={"id"}).items():
        setattr(book, field, value)
    
    db.commit()
    db.refresh(book)
    return book

# PATCH /api/books/{book_id} - Частичное обновление книги (требуется аутентификация)
@app.patch("/api/books/{book_id}", response_model=Book, tags=["Books"])
async def partial_update_book(book_id: int, book_update: BookUpdate, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db)):
    """
    Частично обновить информацию о книге.
    - **book_id**: ID книги для обновления
    - **book_update**: Данные для обновления (только указанные поля будут изменены)
    Обновляет только те поля, которые были переданы в запросе.
    Если книга не найдена, возвращается ошибка 404.
    """
    book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Книга с ID {book_id} не найдена"
        )
    
    update_data = book_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)
    
    db.commit()
    db.refresh(book)
    return book

# GET /api/stats/books - Получение статистики
@app.get("/api/stats/books", tags=["Statistics"])
async def get_statistics(db: Session = Depends(get_db)):
    """
    Получить статистику по книгам.
    Возвращает общее количество книг, распределение по авторам и векам.
    """
    from collections import Counter

    books = db.query(BookDB).all()
    total_books = len(books)
    authors = Counter(book.author for book in books)
    centuries = Counter(book.year // 100 + 1 for book in books)

    return {
        "total_books": total_books,
        "books_by_author": dict(authors),
        "books_by_century": {f"{century} век": count for century, count in centuries.items()}
    }

# DELETE /api/books/{book_id} - Удаление книги (требуется аутентификация)
@app.delete("/api/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Books"])
async def delete_book(book_id: int, api_key: str = Depends(verify_api_key), db: Session = Depends(get_db)):
    """
    Удалить книгу по ID.
    - **book_id**: ID книги для удаления
    Удаляет книгу из системы.
    Если книга не найдена, возвращается ошибка 404.
    """
    book = db.query(BookDB).filter(BookDB.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Книга с ID {book_id} не найдена"
        )

    db.delete(book)
    db.commit()
    return

# Точка входа для запуска приложения
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
