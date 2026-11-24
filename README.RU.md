# 🍰 Capability Slice Architecture

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/github/license/MairwunNx/Capability-Slice-Architecture"></a>
  <a href="https://github.com/MairwunNx/Capsa"><img alt="Implementation: Capsa" src="https://img.shields.io/badge/implementation-Capsa-7F52FF?logo=kotlin&logoColor=white"></a>
  <img alt="Languages: English, Russian" src="https://img.shields.io/badge/languages-en%20%7C%20ru-blue">
</p>

🍰 **Capability Slice Architecture** (CSA) — архитектура клиентских приложений с декларативным UI: Compose, Compose Multiplatform, SwiftUI, Avalonia.FuncUI. Вы делите экран на маленькие capability, по одной на пользовательский сценарий, и каждая владеет своим slice состояния.

[English version](README.md)

Факт попадает в runtime, capability решает, что он значит для её slice, а остальное делает runtime: сохраняет новый slice, запускает работу и отдаёт эффекты хосту.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/flow-dark.svg">
  <img alt="Как факт проходит через экран: UI отправляет intent, runtime передаёт факт capability, capability возвращает решение, работа отвечает сигналом, проекция превращает новый slice в UI-модель, а хост исполняет эффект" src="docs/images/flow-light.svg">
</picture>

Экран перестаёт быть одним большим классом. Каждый сценарий становится своей capability со своим slice, а UI рисует эти slice рядом.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/screen-split-dark.svg">
  <img alt="Экран до и после разделения: один класс, который владеет поиском, таймером, списком, лайками, формой, навигацией и аналитикой, превращается в пять capability, у каждой свой slice" src="docs/images/screen-split-light.svg">
</picture>

## Что вы получаете

- ✏️ **Сценарий меняется в одном месте.** Лайк, поиск и таймер живут каждый в своей capability, поэтому правка одного не задевает код другого.
- ⏳ **Асинхронность описана данными и отменяется сама.** Capability возвращает работу с ключом и политикой. Runtime запускает её, отменяет устаревший запрос при втором нажатии и отбрасывает его запоздалый ответ.
- 🚪 **Побочные эффекты выходят через одну дверь.** Навигация, снекбары и аналитика покидают логику как эффекты, и исполняет их только хост.
- 🧪 **Логика тестируется без UI.** Capability — чистая функция от slice и факта. Тест отправляет факты и проверяет slice и эффекты: без эмулятора и без моков фреймворка.
- 🛡️ **Новый факт не ломает соседний сценарий.** Каждая capability объявляет, какие факты она обрабатывает, а остальные runtime ей не доставляет.
- 🤖 **Агенты следуют правилам.** Правила короткие и формальные, поэтому ИИ-агент пишет capability, которая им соответствует, а ревью проверяет её по пунктам.

## Пять правил

| # | Правило | Что это значит |
|---|---|---|
| 1 | **Разделяйте по сценариям** | Capability владеет пользовательским сценарием: лайком, поиском, таймером. Никогда не блоком вёрстки. |
| 2 | **Хост собирает, а не думает** | Точка входа UI собирает slice, отправляет интенты и исполняет эффекты. Продуктовых условий в ней нет. |
| 3 | **Runtime — единственная шина** | Capability не импортирует другую capability и не читает её slice. Они общаются через факты. |
| 4 | **Побочные эффекты живут на краю** | Логика описывает навигацию, снекбар и аналитику как эффекты, а исполняет их хост. Сами роутер и снекбар в логику не попадают. |
| 5 | **Decider остаётся маленьким** | Примерно 150 строк или 12 фактов. Больше — делите capability. |

## Одна capability, один тест

Лайк появляется сразу, сохраняется в фоне и откатывается, если сохранить не удалось. Пример написан на [Capsa](https://github.com/MairwunNx/Capsa), реализации CSA на Kotlin.

`LikeSlice.kt` — состояние сценария:

```kotlin
data class LikeSlice(val liked: Boolean = false, val likes: Int = 0)
```

`LikeFacts.kt` — что приходит в capability и что уходит из неё:

```kotlin
sealed interface LikeIntent : Intent
data object LikeClicked : LikeIntent

sealed interface LikeSignal : Signal
data class LikeSaved(val likes: Int) : LikeSignal
data object LikeFailed : LikeSignal

data object ShowLikeError : Effect
```

`LikeApi.kt` — порт, через который работа ходит в сеть:

```kotlin
fun interface LikeApi {
    suspend fun setLiked(liked: Boolean): Int
}
```

`Likes.kt` — сама capability:

```kotlin
private val SAVE = WorkKey("save")

// Only a host or a test harness provides this scope.
context(_: CapabilityScope)
fun likes(api: LikeApi) = capability<LikeSlice, LikeIntent, LikeSignal>(name = "likes", initial = LikeSlice()) {
    val works = object {
        fun save(liked: Boolean) = work(key = SAVE, onError = { LikeFailed }) { LikeSaved(api.setLiked(liked)) }
    }

    onIntent<LikeClicked> { state, _ ->
        val liked = !state.liked
        // The heart turns red at once. The request is only described here: the runtime runs it.
        Decision(state = state.copy(liked = liked, likes = state.likes + if (liked) 1 else -1), work = works.save(liked))
    }
    onSignal<LikeSaved> { state, saved -> Decision(state = state.copy(likes = saved.likes)) }
    onSignal<LikeFailed> { state, _ ->
        Decision(state = state.copy(liked = !state.liked, likes = state.likes + if (state.liked) -1 else 1), effect = ShowLikeError)
    }
}
```

Capability сама не ходит в сеть. Она возвращает работу, а runtime запускает её и превращает ответ или ошибку в сигнал. Поэтому тест гоняет настоящий runtime в виртуальном времени с фейковым API, без устройства и без библиотеки моков.

`LikesTest.kt`:

```kotlin
@Test
fun `a failed save rolls the like back`() = runTest {
    val likes = inCapabilityScope { likes(api = { error("offline") }) }
    val harness = capsaHarness(likes)

    harness.append(LikeClicked)
    harness.runCurrent()

    assertEquals(LikeSlice(liked = false, likes = 0), harness.stateOf(likes))
    assertEquals(listOf(ShowLikeError), harness.effects)
}
```

Откат здесь намеренно упрощён. [Честный оптимистичный лайк](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Work-as-data#the-honest-optimistic-like) выдерживает и два быстрых нажатия.

## Реализации

| Реализация | Платформы | Статус |
|---|---|---|
| 📦 [Capsa](https://github.com/MairwunNx/Capsa) | Kotlin Multiplatform: Android, iOS, macOS и JVM, с Compose Multiplatform | превью 0.99 |

Каждая реализация даёт одни и те же гарантии: одна очередь фактов, устаревшие сигналы отбрасываются, каждый эффект доставляется один раз. Все гарантии — на странице [Implementations](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Implementations).

## Откуда идея

CSA выросла из [Feature-Action Architecture](https://github.com/MairwunNx/Feature-Action-Architecture), моей архитектуры для бэкенда. FAA делит бэкенд по доменам и делает каждое действие явным. CSA переносит ту же идею в клиентские приложения, где состояние живёт на экране, а UI перерисовывается из него.

## Документация

Спецификация целиком — в [вики](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki) (на английском):

- [Why](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Why): чем плоха одна большая вью-модель и что меняет CSA.
- [Vocabulary](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Vocabulary) и [Five rules](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Five-rules): каждый термин и каждое правило с примером нарушения и исправления.
- [Data flow](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Data-flow), [Work as data](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Work-as-data) и [Effects](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Effects): один проход факта, ключи и политики, одна дверь наружу.
- [Projections](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Projections), [Boundaries](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Boundaries) и [Structure](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Structure): от slice к UI-модели, порты и проводка, пакеты экрана.
- [Testing](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Testing): что тестировать и как обойтись без UI.
- [Comparison](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Comparison) и [Tradeoffs](https://github.com/MairwunNx/Capability-Slice-Architecture/wiki/Tradeoffs): CSA рядом с MVVM, MVI, TCA и Elm, и чего CSA не решает.

## Связанные проекты

- **[Capsa](https://github.com/MairwunNx/Capsa)** — реализация CSA на Kotlin Multiplatform.
- **[Feature-Action Architecture](https://github.com/MairwunNx/Feature-Action-Architecture)** — моя архитектура для бэкенда, то же чутьё: делим по доменам, одна функция на одну работу.

> 🫡 Made by Pavel Erokhin (Павел Ерохин), aka mairwunnx.
