# Хроніст

AI-компаньйон для дослідників українських архівів. Розширення Chrome читає рукописні скани на архівному порталі, пояснює терміни й дати з посиланням на джерела, а підтверджені людьми транскрипції потрапляють у відкритий шар Commons під CC BY 4.0.

[![CI](https://github.com/code-by-accident/Khronist-real-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/code-by-accident/Khronist-real-platform/actions/workflows/ci.yml)
[![Код: Apache-2.0](https://img.shields.io/badge/%D0%BA%D0%BE%D0%B4-Apache--2.0-blue)](LICENSE)
[![Транскрипції: CC BY 4.0](https://img.shields.io/badge/%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BA%D1%80%D0%B8%D0%BF%D1%86%D1%96%D1%97-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/deed.uk)

[Сайт](https://khronist.org) · [Пошук у Commons](https://app.khronist.org) · [API](https://api.khronist.org/health) · [Посібник користувача](docs/user-guide.md)

![Пошук у Commons на app.khronist.org: запит «Коваленко» знаходить підтверджений запис метричної книги ЦДІАК України, ф. 127, оп. 1078, спр. 2276](docs/images/web-search.png)

## Для чого це

Мільйони аркушів українських архівів оцифровано, але читати їх важко: рукопис, дореформена орфографія, скорочення, юліанські дати. Хроніст перетворює скан на джерело, з яким можна працювати: прочитати запис, пояснити незнайомі слова, оформити цитату й зробити прочитане доступним для пошуку.

Проєкт створено для Культурного хакатону OBRIO × МУР, трек «Історія».

**In English.** Khronist is an AI companion for researchers of Ukrainian archives. A Chrome extension reads handwritten scans on the archive portal, explains terms and dates using a reference corpus with cited sources, and lets people translate the text into modern Ukrainian, correct it and confirm it. Confirmed transcriptions go into an open layer, Commons, published under CC BY 4.0 and searchable at [app.khronist.org](https://app.khronist.org). The same reading, explanation and search are available to AI assistants through an MCP server. The interface and documentation are in Ukrainian. The extension currently works on ARCHIUM of the Central State Historical Archive of Ukraine in Kyiv; the code is under Apache-2.0.

## Можливості

- Читання рукопису. Виділіть запис на скані, і через кілька секунд він стане текстом: рядок у рядок, непевні слова позначені, обрізаний текст чи пошкоджений папір видно в попередженнях.
- Переклад українською під рядками російськомовного запису, з тією самою нумерацією рядків.
- Імена, місця, дати й терміни як окремі елементи. Пояснення будується лише за довідковим корпусом, з джерелом і ліцензією; дата переводиться зі старого стилю в новий.
- Чат із запитаннями про запис і його терміни. Коли джерела немає, Хроніст так і каже, а не вигадує відповідь.
- Правка рядків і підтвердження: перевірені люди підтверджують текст, і він стає частиною Commons.
- Цитата за ДСТУ 8302:2015, у Markdown або простим текстом.
- Пошук у Commons за прізвищем, ім'ям чи назвою села з урахуванням давніх написань.
- MCP-сервер: читання, пояснення й пошук в AI-асистентах із підтримкою MCP.

## Спробувати за хвилину

- Пошук без встановлення: відкрийте [app.khronist.org](https://app.khronist.org) і введіть, наприклад, «Коваленко». Типово показано лише підтверджені людьми записи.
- Читання скану: відкрийте [метричну книгу 1896 року в ARCHIUM](https://archium.cdiak.archives.gov.ua/file-viewer/131976) із встановленим розширенням (кроки нижче) і виділіть запис на аркуші.

## Як користуватися

Докладно, з усіма станами й помилками, — у [посібнику користувача](docs/user-guide.md). Коротко:

1. Встановіть розширення. У Chrome Web Store його ще немає, тому збирайте з коду: `pnpm install`, потім `pnpm --filter @khronist/extension build`. У `chrome://extensions` увімкніть режим розробника й оберіть теку `apps/extension/.output/chrome-mv3`. Потрібні Chrome 116+, Node.js 24 і pnpm 12.16.1.
2. Відкрийте скан у переглядачі [ARCHIUM ЦДІАК України](https://archium.cdiak.archives.gov.ua) (адреса з `/file-viewer/`) і відкрийте панель Хроніста: іконка розширення або Alt + Shift + X.
3. Натисніть «Виділити фрагмент» і обведіть запис на аркуші цілком. Рядки з'являться в панелі, коли читання завершиться.
4. Звіряйте з оригіналом слова, підкреслені пунктиром: це місця, де модель не впевнена.
5. Клікайте імена, місця, дати й терміни, щоб побачити пояснення, або ставте запитання у вкладці «Спитати».
6. Для правок і підтвердження увійдіть за кодом із листа. Входити, щоб читати, пояснювати, питати й цитувати, не потрібно.
7. Шукайте серед прочитаного на [app.khronist.org](https://app.khronist.org): встановлювати нічого не треба.
8. Щоб користуватися тим самим в AI-асистенті, підключіть [MCP-сервер](apps/mcp/README.md).

## Стан проєкту

| Частина | Стан |
| --- | --- |
| API | працює: `https://api.khronist.org` |
| Пошук у Commons | працює: `https://app.khronist.org` |
| Розширення Chrome | працює на ARCHIUM ЦДІАК України; у Chrome Web Store немає, встановлюється вручну |
| MCP-сервер | запускається локально з клону репозиторію (stdio) |
| Інші портали, нотатник, завантаження власних сканів | поки немає |

## Як це влаштовано

Розширення вирізає виділений фрагмент скану й надсилає його в API. Скан не зберігається: сервер тримає хеш фрагмента, шифр аркуша й прочитаний текст. Мультимодальна модель читає фрагмент у фоновій задачі, потім текст зводиться до сучасної орфографії, з нього беруться сутності, а російськомовний запис перекладається. Результат записується в PostgreSQL, повторне виділення віддається з кешу. Правка створює нову версію, а підтвердження людиною робить її публічною під CC BY 4.0. Пояснення й чат відповідають лише за довідковим корпусом із `services/knowledge`.

Схему компонентів, потоки даних і модель бази описано в [docs/architecture.md](docs/architecture.md).

## Розробка

Потрібні Node.js 24+, pnpm 12.16.1, Docker для локального PostgreSQL 18 і, для `services/knowledge`, uv з Python 3.12.

```sh
pnpm install
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d
pnpm db:migrate
pnpm dev
```

У PowerShell замість `cp` — `Copy-Item .env.example .env`. API слухає `http://localhost:3000`, `GET /health` має відповісти `{"ok":true,...}`. З `LLM_FIXTURES=1` з `.env.example` читання фікстурне, тож ключі моделей і гроші не потрібні.

Перед комітом: `pnpm lint && pnpm typecheck && pnpm test`. Усі команди, налаштування, міграції й типові проблеми — в [docs/development.md](docs/development.md).

## Структура репозиторію

| Тека | Що там |
| --- | --- |
| [apps/api](apps/api/README.md) | API на Fastify 5 і Drizzle, фонові задачі, міграції |
| [apps/extension](apps/extension/README.md) | розширення Chrome на WXT і React 19, бічна панель |
| [apps/web](apps/web/README.md) | вебзастосунок пошуку в Commons на Vite і React 19 |
| [apps/mcp](apps/mcp/README.md) | MCP-сервер, тонкий клієнт публічного API |
| [packages/contracts](packages/contracts) | Zod-схеми й типи, спільні для всіх застосунків |
| [packages/ui](packages/ui/README.md) | дизайн-система: тема й компоненти |
| [packages/prompts](packages/prompts) | промпти для моделей і схеми відповідей |
| [packages/config](packages/config) | спільна базова конфігурація TypeScript |
| [services/knowledge](services/knowledge/README.md) | довідковий корпус, словник варіантів написання, оцінка якості |
| [docs/demo-fund](docs/demo-fund/README.md) | демонстраційний фонд: аркуші й готові прочитання |
| [infra](infra) | локальний PostgreSQL |
| [.railway](.railway) | опис розгортання API на Railway |

## Документація

| Документ | Для кого |
| --- | --- |
| [Посібник користувача](docs/user-guide.md) | дослідники: встановлення, читання, правка, цитата, пошук |
| [Архітектура](docs/architecture.md) | розробники: компоненти, потоки даних, модель бази |
| [Довідник API](docs/api.md) | розробники й інтегратори: маршрути, запити, відповіді, помилки |
| [Конфігурація](docs/configuration.md) | ті, хто розгортає: змінні середовища |
| [Розробка](docs/development.md) | розробники: запуск, команди, тести, міграції, розгортання |
| [Commons](docs/commons.md) | дослідники й ті, хто використовує дані: що зберігається, ліцензія, як отримати й цитувати |
| [Корпус](docs/corpus.md) | історики: як додати або виправити статтю довідкового корпусу |
| [Як долучитися](CONTRIBUTING.md) | автори змін: гілки, коміти, перевірки, правила коду |
| [Журнал змін](CHANGELOG.md) | що змінилося в кожному випуску |
| [Безпека](SECURITY.md) | як повідомити про вразливість |

## Ліцензія

Код — [Apache-2.0](LICENSE). Підтверджені транскрипції Commons публікуються під [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.uk). Скани належать архівам і в репозиторії не зберігаються.
