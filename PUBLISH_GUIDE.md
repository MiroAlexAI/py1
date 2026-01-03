# Руководство по публикации ChatList Professional

Это руководство поможет вам правильно подготовить приложение к публикации в GitHub и настроить автоматизацию.

## 1. Подготовка репозитория
Убедитесь, что все файлы находятся в актуальном состоянии. 
Папка `docs/` зарезервирована для вашего лендинга (**GitHub Pages**).

### Перенос изображения
1. Возьмите сгенерированный файл `chatlist_hero_mockup.png`.
2. Переименуйте его в `hero.png`.
3. Поместите его в папку `docs/assets/`.

## 2. GitHub Releases (Публикация программы)
Чтобы пользователи могли скачивать готовый `.exe` файл:

### Вариант А: Ручная сборка (PyInstaller)
1. Установите PyInstaller: `pip install pyinstaller`.
2. Соберите приложение:
   ```bash
   pyinstaller --noconsole --onefile --name "ChatList_Pro" --add-data "chatlist.db;." main.py
   ```
3. Перейдите в раздел **Releases** на GitHub.
4. Нажмите **Create a new release**.
5. Загрузите файл `dist/ChatList_Pro.exe`.

### Вариант Б: GitHub Actions (Автоматизация)
Я подготовил шаблон `.github/workflows/release.yml`. Если вы его активируете, GitHub будет сам собирать EXE при каждом новом теге (например, `v1.0.0`).

## 3. GitHub Pages (Запуск лендинга)
1. Перейдите в **Settings** вашего репозитория на GitHub.
2. Слева выберите раздел **Pages**.
3. В разделе **Build and deployment** выберите:
   - Source: `Deploy from a branch`
   - Branch: `main` (или ваша рабочая ветка)
   - Folder: `/docs`
4. Нажмите **Save**. Через 1-2 минуты ваш сайт будет доступен по адресу: `https://[username].github.io/py1/`.

## 4. Обновление README
Обновите ваш основной `README.md`, чтобы он выглядел профессионально и содержал ссылки на сайт и документацию.

---
*Документация подготовлена SRE инженером Antigravity.*
