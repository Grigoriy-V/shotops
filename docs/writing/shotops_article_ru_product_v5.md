# ShotOps: Scene as Code для AI-native production

ShotOps начался с простой идеи: **что если сцена в CG-пайплайне будет существовать как код, а не только как файл внутри DCC?**

Camera, blocking, objects, transforms, timing, references и generation settings описываются как читаемый structured state. Agent может этот state создавать и менять. Blender — собирать из него сцену и рендерить blockout. Generative model — превращать blockout в finished shot. Git — хранить историю изменений.

> **Agents author it. DCCs execute it. AI models render it. Git remembers it.**

---

## 1. Первый production case — NYC

**[IMAGE 1 — INSERT HERE]**  
`NYC blocking / H3 base`

Первый production case — десятисекундный пролёт по NYC street.

В сцене 104 объекта, почти полностью собранных из простых primitives. Камера с 20 mm lens проходит около 112 метров, дважды пролетает примерно в 0.95 м от машин, поднимается по стене и выходит на крышу.

Слева — structured Blender blockout.  
Справа — результат self-hosted MiniMax H3.

H3 сохраняет основную camera motion, timing и staging, хотя исходная сцена очень грубая.

До этого тот же shot проходил через Seedance 2.

То есть менялся renderer, а source scene оставалась той же.

И это главный тезис ShotOps: **shot не должен принадлежать конкретному DCC, agent или video model.**

---

## 2. Новый production loop: от handoffs к NLP

Классический production loop появился не потому, что это идеальный способ создавать изображения.

Он появился потому, что инструменты требуют специализированных операторов.

Обычно это выглядит примерно так:

**Director / Art Director**  
→ Supervisor  
→ Artist  
→ DCC  
→ Preview  
→ Supervisor  
→ Director  
→ Notes  
→ Artist

Каждый iteration проходит через несколько handoffs.

Если scene становится structured state, а agent умеет её собирать и менять, появляется другой loop:

**Creator / Director / Art Director**  
→ natural language  
→ Agent  
→ Scene  
→ Render  
→ iteration

Человек может сказать:

- «камера ближе»;
- «машина появляется раньше»;
- «оставь staging, но верни предыдущий lens»;
- «сделай три варианта движения камеры»;
- «персонаж должен занимать треть кадра».

Agent меняет не только prompt.

Он меняет **саму scene state**.

После этого Blender пересобирает blocking, а AI renderer возвращает визуально законченный вариант.

Главное здесь в том, что каждый iteration остаётся **редактируемой и versioned сценой**, а не просто новой картинкой.

Для previs, tenders, pitches и early development это может радикально сократить путь от идеи до визуального результата — особенно там, где один человек ещё только формулирует, чего именно он хочет.

---

## 3. Scene as Code: IT-принципы внутри CG production

В традиционном CG production сцена обычно живёт внутри `.blend`, `.ma`, `.hip` или другого binary DCC file. История существует вокруг неё — версии, renders, playblasts, ShotGrid / Shotgun, комментарии и ссылки — но сами изменения остаются непрозрачными.

`v018` отличается от `v017`, но чтобы понять чем именно, часто приходится открывать обе версии и восстанавливать контекст вручную.

В ShotOps scene хранится как structured text:

- `camera`
- `blocking`
- `objects / assets`
- `transforms`
- `timing`
- `look references`
- `generation settings`

Blender scene, blockouts, previews и generations становятся **derived artifacts**, а source of truth смещается в versioned scene state.

Это позволяет перенести в CG привычные IT-принципы:

- Git diff вместо комментария «updated camera»;
- revert одного изменения вместо rollback всей сцены;
- branches для параллельных staging ideas;
- merge независимых изменений;
- воспроизводимость конкретного scene state;
- читаемую историю того, как shot менялся.

Diff может быть буквально таким:

`camera.focal_length: 24 → 20`

`car_02.position.x: 4.8 → 5.4`

`shot.duration: 8.0 → 10.0`

`look_reference: ref_a → ref_b`

Это и есть **Scene as Code**: production state становится inspectable, diffable и reversible, а binary DCC files перестают быть единственным местом, где живёт сцена.


## 4. Agent как production operator

Agent — production operator внутри ShotOps.

Он может:

- собрать scene;
- построить camera;
- расставить objects;
- изменить timing;
- запустить Blender;
- получить previews;
- отправить generation;
- сравнить iterations.

При этом он работает не через хаотичный GUI state, а через config.

И проверяет себя до дорогой generation.

Порядок такой:

**1. Deterministic checks**  
camera path, speed, acceleration, stalls, collisions, closest approach.

**2. Multi-view render**  
shot camera, top, front, 3/4 — чтобы увидеть layout и camera path.

**3. Vision review**  
только там, где математическая проверка уже не отвечает на вопрос.

Так появился `audit`: он использует ту же baked camera path, что и render, и может остановить iteration до generation, если camera проходит через geometry.

Принцип простой:

> **Deterministic checks first. Vision where it actually adds information.**

---

## 5. Renderer тоже не должен определять pipeline

Следующий важный шаг — model abstraction.

NYC shot уже проходил через proprietary Seedance 2 и через self-hosted MiniMax H3 на Modal.

**[IMAGE 2 — INSERT HERE]**  
`2×2 grid: blockout / Seedance 2 / H3 base / H3 spectrum or H3 8-step`

Один и тот же scene state. Несколько render backends.

В текущих tests:

- **Seedance 2** — около **2:34**, **$1.05**, низкий operational overhead;
- **H3 base** — около **21:03**, примерно **$1.06 GPU cost**, strongest H3 structural fidelity;
- **H3 spectrum** — около **13:57**, примерно **$0.70**;
- **H3 8-step distilled** — около **6:51**, примерно **$0.35**, быстрее и дешевле, но слабее по structure.

Эти цифры показывают разные production trade-offs.

Важно, что production pipeline уже можно строить не только вокруг proprietary service.

Self-hosted open weights дают:

- контроль над weights;
- sampler;
- steps;
- model lifecycle;
- deployment;
- стоимостью;
- отсутствием зависимости от того, будет ли provider завтра поддерживать тот же endpoint.

Для ShotOps это означает:

**Scene State**  
→ **Model Adapter**  
→ Seedance / self-hosted H3 / future model

С H3 это особенно хорошо видно. В open weights есть H3-Base, но нет hosted **H3-Context-IR**, который превращает свободный multimodal input в structured representation для модели. В ShotOps большая часть этой работы уже сделана самой системой: shot существует как код, subjects, camera, timing и scene structure уже явно описаны, а agent знает весь этот state и не должен заново угадывать его из prompt. Поэтому он может собрать model-specific representation напрямую из scene config и передать его adapter'у. Для другой модели меняется только этот слой перевода — не сама сцена и не production pipeline.

Меняется renderer.

Не меняется способ авторинга shot.

---

## 6. От одного shot к sequence

NYC проверял один длинный continuous shot.

Следующий experiment — `spot` — был специально другим.

Там четыре blockout shots с тремя cuts были собраны в один reference video и отправлены в H3 одной generation.

Один character reference задавал персонажа сразу для нескольких shots.

**[IMAGE 3 — INSERT HERE]**  
`SPOT blockout sequence / H3 generated sequence`

Cuts в целом сохранились, и один и тот же character переносится между shots.

Camera adherence и performance direction пока нестабильны, но для ShotOps ключевой результат:

> **Generation unit не обязательно должен быть одним shot. Он может быть sequence.**

Это открывает production path, где не генерировать каждый shot независимо и собирать edit потом, а использовать уже смонтированный blocking как structural reference для целой последовательности.

---

## 8. Кому это нужно и куда идёт ShotOps

Сегодня рынок разделён между двумя крайностями.

С одной стороны — prompt-first AI tools: быстрые, но production state легко распадается между prompts, chats, provider history и folders.

С другой — traditional studio pipeline: высокий контроль, но вместе с ShotGrid, DCC integrations, asset management, render infrastructure и отдельной pipeline team.

ShotOps занимает пространство между ними:

**Prompt-to-video tools**  
низкий infrastructure overhead / низкий production control

**ShotOps**  
низкий или средний overhead / высокий control и traceability

**Traditional studio pipeline**  
высокий overhead / очень высокий control

Основная аудитория:

- solo creators;
- small AI-native studios;
- small / medium production teams.

Для больших studios естественный entry point — previs, tenders, pitches, early creative development и AI departments.

Коротко:

> **Studio-level production discipline without studio-level infrastructure.**

Дальше ShotOps может вырасти из системы для scenes и shots в общий production layer:

**Idea → Previs / Tender → Shots / Sequences → CG + AI Generation → Edit → Delivery**

Под ним — version history, agents, assets, model adapters, approvals, generation logs, shot status, cost и time analysis.

Конечная цель — не ещё один AI renderer и не просто ускорение существующего CG pipeline.

Цель — **альтернатива DCC-centric production**, где одна versioned production system связывает человека, agents, DCC, open / proprietary models и весь путь от идеи до delivery.
