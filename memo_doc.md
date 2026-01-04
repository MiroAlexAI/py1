---
version: 2.0
project: ChatList Professional
author: MiroAlex AI
last_updated: 2025-01-04
tags: [memory-bank, documentation, chatlist, pyqt6, ai-integration]
---

# 🧠 Memory Bank для ChatList Professional

Центральный хаб для хранения знаний, архитектурных решений и документации проекта ChatList Professional.

## 🗺️ Навигация по структуре

```
.mem
├── .memory_bank/
│   ├── README.md                  # Этот файл - навигация
│   ├── project_overview.md        # Обзор проекта и видение
│   ├── tech_stack.md              # Технологический стек
│   ├── current_tasks.md           # Живая Kanban-доска
│   ├── decisions/                 # Architecture Decision Records (ADR)
│   │   ├── adr_001_database.md
│   │   ├── adr_002_ui_framework.md
│   │   └── adr_003_ai_integration.md
│   ├── patterns/                  # Архитектурные паттерны
│   │   ├── api_standards.md
│   │   ├── error_handling.md
│   │   ├── ai_model_patterns.md
│   │   └── pyqt6_components.md
│   ├── guides/                    # Практические руководства
│   │   ├── coding_standards.md
│   │   ├── testing_strategy.md
│   │   ├── database_guide.md
│   │   └── security_guide.md
│   ├── specs/                     # Технические задания
│   │   ├── feature_triple_prompt.md
│   │   ├── feature_model_manager.md
│   │   └── feature_results_journal.md
│   ├── workflows/                 # Пошаговые инструкции
│   │   ├── bug_fix.md
│   │   ├── new_feature.md
│   │   ├── feature_development.md
│   │   └── release_process.md
│   ├── templates/                 # Шаблоны для быстрого создания
│   │   ├── feature_template.md
│   │   ├── adr_template.md
│   │   └── bug_report_template.md
│   └── glossary.md               # Словарь терминов проекта
```

## 🚀 Быстрый старт

### Для ChatList Professional:
1. **Изучите основы**: [project_overview.md](.memory_bank/project_overview.md)
2. **Поймите стек**: [tech_stack.md](.memory_bank/tech_stack.md)
3. **Текущие задачи**: [current_tasks.md](.memory_bank/current_tasks.md)
4. **Архитектурные решения**: [decisions/](.memory_bank/decisions/)

### Для разработки:
1. **Следуйте стандартам**: [coding_standards.md](.memory_bank/guides/coding_standards.md)
2. **Используйте паттерны**: [patterns/](.memory_bank/patterns/)
3. **Тестируйте**: [testing_strategy.md](.memory_bank/guides/testing_strategy.md)

## 🧩 Как использовать Memory Bank

### 📝 Ежедневная работа:
- **Новые задачи** → Добавляйте в `current_tasks.md`
- **Решения** → Документируйте в `decisions/` как ADR
- **Паттерны** → Сохраняйте в `patterns/`
- **Проблемы** → Используйте `workflows/bug_fix.md`

### 🔄 Жизненный цикл:
1. **Идея** → `specs/feature_*.md`
2. **Разработка** → `workflows/feature_development.md`
3. **Решение** → `decisions/adr_*.md`
4. **Паттерн** → `patterns/*.md`
5. **Готово** → Обновить `current_tasks.md`

## 🎯 Специфично для ChatList

### AI Интеграция:
- [ai_model_patterns.md](.memory_bank/patterns/ai_model_patterns.md) - паттерны работы с AI
- [feature_triple_prompt.md](.memory_bank/specs/feature_triple_prompt.md) - тройной промпт

### PyQt6 Компоненты:
- [pyqt6_components.md](.memory_bank/patterns/pyqt6_components.md) - UI паттерны
- [coding_standards.md](.memory_bank/guides/coding_standards.md) - стандарты кода

### Безопасность:
- [security_guide.md](.memory_bank/guides/security_guide.md) - управление API ключами
- [error_handling.md](.memory_bank/patterns/error_handling.md) - обработка ошибок

## 🛠️ Интеграция с инструментами

### Cursor IDE:
```bash
# Поиск файлов в Memory Bank
Ctrl+Shift+P → "Memory Bank: Find File"

# Создание нового файла по шаблону
Ctrl+Shift+P → "Memory Bank: New from Template"
```

### Автоматизация:
```bash
# Настройка структуры
python scripts/setup_memory_bank.py

# Валидация документации
python scripts/validate_docs.py
```

## 📊 Метаданные и версия

- **Версия**: 2.0
- **Проект**: ChatList Professional
- **Последнее обновление**: 2025-01-04
- **Совместимость**: PyQt6, Python 3.8+

## 🔄 Правила обновления

1. **Версионирование**: Обновляйте `last_updated` при изменениях
2. **Ссылки**: Проверяйте внутренние ссылки при добавлении файлов
3. **Согласованность**: Следуйте установленным шаблонам
4. **Актуальность**: Регулярно обновляйте `current_tasks.md`

## 📞 Поддержка и вклад

### Вопросы по структуре:
- Смотрите [glossary.md](.memory_bank/glossary.md) для терминов
- Используйте шаблоны в `templates/`
- Следуйте workflow в `workflows/`

### Вклад в проект:
1. Создайте ADR для архитектурных решений
2. Добавляйте паттерны в `patterns/`
3. Обновляйте документацию при изменениях

---

**💡 Совет**: Начните с `project_overview.md` для понимания контекста, затем используйте `current_tasks.md` для отслеживания прогресса.

**🔗 Быстрая навигация**: [tech_stack.md](.memory_bank/tech_stack.md) → [current_tasks.md](.memory_bank/current_tasks.md) → [decisions/](.memory_bank/decisions/)