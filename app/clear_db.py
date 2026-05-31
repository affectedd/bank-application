from database import engine
import models


def reset_database():
    print("Удаление всех таблиц...")
    # drop_all полностью удаляет таблицы вместе со всеми данными
    models.Base.metadata.drop_all(bind=engine)

    print("Создание новых пустых таблиц...")
    # create_all создает их заново, но уже пустыми
    models.Base.metadata.create_all(bind=engine)

    print("База данных успешно очищена!")


if __name__ == "__main__":
    reset_database()