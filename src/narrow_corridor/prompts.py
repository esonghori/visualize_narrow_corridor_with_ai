"""Prompt templates for the Narrow Corridor scoring pipeline.

Two improvements over the original notebook prompts:

* An explicit, anchored 0-10 rubric for both axes, so scores are comparable
  across countries and across models instead of free-floating.
* Neutral, non-leading framing: the model is asked to weigh evidence both ways,
  avoid presentism, and not assume the country drifts toward any corner.

The Chain-of-Thought (events/trends first) and In-Context Learning (prior scores
fed forward) structure of the original methodology is preserved.

Language ablation
-----------------
Every prompt builder takes a ``lang`` argument (default ``"en"``). ``"en"`` runs
the original English code path unchanged (byte-identical output, so existing
cache keys and saved runs are undisturbed). ``"fr"`` / ``"zh"`` / ``"fa"`` swap
the instructional prose for a faithful translation while keeping the requested
JSON *field names* in English -- those are the contract with ``PeriodScore``
(models.py) and the ``<...>`` regex fallback (llm.py), so they must not change.
``period_to_text`` and the ICL score accumulator are language-neutral and are
not translated. See ``paper/experiments/lang_ablation.py``.
"""

from __future__ import annotations

from narrow_corridor.models import Period, period_to_text

LANGS = ("en", "fr", "zh", "fa", "es", "ar")

# Shared rubric + neutrality guidance injected into every scoring prompt.
RUBRIC = """\
Use this fixed 0-10 rubric so values are comparable across periods and countries.

STATE POWER — the capacity of the state to enforce its will, administer
territory, collect taxes, and project authority:
  0-2  collapsed / nonexistent: no effective central authority.
  3-4  weak: limited reach, contested control, depends on local powerbrokers.
  5-6  moderate: functioning bureaucracy and military with real but bounded reach.
  7-8  strong: pervasive administration, effective coercion and revenue capacity.
  9-10 overwhelming: near-total penetration of society; little it cannot enforce.

SOCIETY POWER — the capacity of civil society to organize, mobilize, hold the
state accountable, and resist domination (norms, associations, press, protest,
independent institutions):
  0-2  atomized: no autonomous organization; collective action near-impossible.
  3-4  weak: sporadic, easily suppressed mobilization.
  5-6  moderate: real associational life and periodic effective mobilization.
  7-8  strong: dense civic institutions routinely constraining the state.
  9-10 dominant: society pervasively shapes and checks state action.

Guidance for objectivity:
- Judge each period on its own terms; do not assume the country trends toward
  liberty, autocracy, or any particular corner of the space.
- Weigh evidence both for and against a shift before settling on a number.
- Avoid presentism: score by the standards and information of the period, not
  by how things turned out later.
- These two axes are independent: a strong state can coexist with a strong or a
  weak society. Score them separately."""


def events_trends_prompt(country: str, period: Period, lang: str = "en") -> str:
    period_text = period_to_text(period)
    if lang != "en":
        return _ET_I18N[lang].format(country=country, period_text=period_text)
    return f"""\
Considering Daron Acemoğlu and James A. Robinson's framework in *The Narrow
Corridor: States, Societies, and the Fate of Liberty*, identify the major
historical events and trends in {country} during {period_text} that materially
affected EITHER the power of the state OR the power of civil society.

Be concrete and specific to {period_text}. Distinguish slow-moving trends
(institutional, economic, demographic) from discrete events. For each item, note
briefly whether it strengthened or weakened the state, society, or both.

Respond with two short bulleted lists:

Trends:
- ...

Events:
- ..."""


def _common_score_framing(
    country: str, start_year: int, end_year: int, lang: str = "en"
) -> str:
    if lang != "en":
        return _FRAMING_I18N[lang].format(
            country=country, start_year=start_year, end_year=end_year,
            rubric=_RUBRIC_I18N[lang],
        )
    return f"""\
You are placing the country of {country} in the 2D space of Acemoğlu and
Robinson's *The Narrow Corridor*: the x-axis is the power of civil society and
the y-axis is the power of the state. We are tracing the path from {start_year}
to {end_year}.

{RUBRIC}"""


def bootstrap_score_prompt(
    country: str, start_year: int, end_year: int, period: Period, lang: str = "en"
) -> str:
    """First-period prompt: emit absolute <society, state> with changes = 0."""
    period_text = period_to_text(period)
    framing = _common_score_framing(country, start_year, end_year, lang)
    if lang != "en":
        return _BOOTSTRAP_I18N[lang].format(
            framing=framing, country=country, period_text=period_text
        )
    return f"""\
{framing}

This is the FIRST period of the trajectory: {period_text}. Establish the
starting point. Estimate the absolute power of civil society and of the state in
{country} during {period_text} using the rubric above. Since there is no prior
period, report both change values as 0.0.

Return a JSON object with exactly these fields:
- society_power (float, 0-10)
- state_power (float, 0-10)
- society_change (float, 0.0)
- state_change (float, 0.0)
- key_event (string, <= ~10 words: the single most defining feature of this period)
- reasoning (string, 1-2 sentences justifying the two power values)"""


def score_prompt(
    country: str,
    start_year: int,
    end_year: int,
    period: Period,
    previous_period: Period,
    events_trends_text: str,
    previous_scores_text: str,
    lang: str = "en",
) -> str:
    """Subsequent-period prompt: condition on this period's events + prior path."""
    period_text = period_to_text(period)
    previous_period_text = period_to_text(previous_period)
    framing = _common_score_framing(country, start_year, end_year, lang)
    if lang != "en":
        return _SCORE_I18N[lang].format(
            framing=framing, country=country, period_text=period_text,
            previous_period_text=previous_period_text,
            events_trends_text=events_trends_text,
            previous_scores_text=previous_scores_text,
        )
    return f"""\
{framing}

Score the period {period_text}, building on the established trajectory. Start
from where {country} stood at the end of {previous_period_text}, then apply the
changes implied by the events and trends below. Report both the per-axis change
and the resulting absolute values (anchored to the rubric, not just to the prior
point). A period with little real change should show changes near 0.0.

Historical events and trends in {period_text}:
{events_trends_text}

Trajectory so far (period: <society_power, state_power>):
{previous_scores_text}

Return a JSON object with exactly these fields:
- society_power (float, 0-10): absolute society power at the end of {period_text}
- state_power (float, 0-10): absolute state power at the end of {period_text}
- society_change (float): society_power change vs. {previous_period_text}
- state_change (float): state_power change vs. {previous_period_text}
- key_event (string, <= ~10 words: the defining event/trend driving the change)
- reasoning (string, 1-2 sentences justifying the values)"""


# ============================================================================
# Non-English variants (language ablation). Only prose is translated; the JSON
# field names below stay English on purpose (see module docstring).
# ============================================================================

_RUBRIC_I18N = {
    "fr": """\
Utilisez ce barème fixe de 0 à 10 afin que les valeurs soient comparables entre
les périodes et les pays.

POUVOIR DE L'ÉTAT — la capacité de l'État à imposer sa volonté, administrer le
territoire, lever l'impôt et projeter son autorité :
  0-2  effondré / inexistant : aucune autorité centrale effective.
  3-4  faible : portée limitée, contrôle contesté, dépendance aux pouvoirs locaux.
  5-6  modéré : bureaucratie et armée fonctionnelles, à la portée réelle mais bornée.
  7-8  fort : administration omniprésente, coercition efficace et capacité de recettes.
  9-10 écrasant : pénétration quasi totale de la société ; peu de choses qu'il ne puisse imposer.

POUVOIR DE LA SOCIÉTÉ — la capacité de la société civile à s'organiser, se
mobiliser, demander des comptes à l'État et résister à la domination (normes,
associations, presse, protestation, institutions indépendantes) :
  0-2  atomisée : aucune organisation autonome ; action collective quasi impossible.
  3-4  faible : mobilisation sporadique, aisément réprimée.
  5-6  modérée : vie associative réelle et mobilisation efficace par intermittence.
  7-8  forte : institutions civiques denses contraignant régulièrement l'État.
  9-10 dominante : la société façonne et contrôle largement l'action de l'État.

Consignes d'objectivité :
- Jugez chaque période selon ses propres termes ; ne supposez pas que le pays
  tend vers la liberté, l'autocratie ou un coin particulier de l'espace.
- Pesez les éléments pour et contre un changement avant d'arrêter un chiffre.
- Évitez le présentisme : notez selon les normes et informations de l'époque,
  non selon la manière dont les choses ont tourné par la suite.
- Ces deux axes sont indépendants : un État fort peut coexister avec une société
  forte ou faible. Notez-les séparément.""",
    "zh": """\
请使用以下固定的 0-10 评分标准，使各时期、各国之间的数值可以相互比较。

国家权力 —— 国家贯彻其意志、治理领土、征收赋税并投射权威的能力：
  0-2  崩溃／不存在：没有有效的中央权威。
  3-4  弱：触及范围有限，控制权受争夺，依赖地方势力。
  5-6  中等：官僚机构与军队运作正常，影响力真实但有限。
  7-8  强：行政管理无处不在，具备有效的强制与财政汲取能力。
  9-10 压倒性：几乎完全渗透社会；几乎没有它无法强制执行的事。

社会权力 —— 公民社会组织、动员、问责国家并抵抗支配的能力（规范、社团、
新闻、抗议、独立机构）：
  0-2  原子化：没有自主组织；集体行动几乎不可能。
  3-4  弱：零星且易被压制的动员。
  5-6  中等：存在真实的社团生活与阶段性的有效动员。
  7-8  强：密集的公民机构经常性地约束国家。
  9-10 主导：社会广泛地塑造并制衡国家行为。

保持客观的指引：
- 就每个时期本身进行判断；不要假定该国趋向自由、专制或空间中的某个特定角落。
- 在确定数值之前，权衡支持与反对某一变化的证据。
- 避免以今度古：按该时期的标准与信息评分，而非按后来的结局评分。
- 这两个维度相互独立：强国家可以与强社会或弱社会并存。请分别评分。""",
    "fa": """\
از این معیار ثابت ۰ تا ۱۰ استفاده کنید تا مقادیر در میان دوره‌ها و کشورها قابل
مقایسه باشند.

قدرت دولت — توانایی دولت در تحمیل اراده‌ی خود، اداره‌ی سرزمین، وصول مالیات و
اعمال اقتدار:
  ۰-۲  فروپاشیده / ناموجود: هیچ اقتدار مرکزی مؤثری وجود ندارد.
  ۳-۴  ضعیف: دسترسی محدود، کنترل مورد مناقشه، وابسته به قدرت‌های محلی.
  ۵-۶  متوسط: بوروکراسی و ارتش کارآمد با دسترسی واقعی اما محدود.
  ۷-۸  قوی: اداره‌ی فراگیر، سرکوب مؤثر و توان درآمدزایی.
  ۹-۱۰ فراگیر: نفوذ تقریباً کامل در جامعه؛ چیز کمی هست که نتواند اعمال کند.

قدرت جامعه — توانایی جامعه‌ی مدنی برای سازمان‌یابی، بسیج، پاسخ‌خواهی از دولت و
مقاومت در برابر سلطه (هنجارها، انجمن‌ها، مطبوعات، اعتراض، نهادهای مستقل):
  ۰-۲  اتمیزه: هیچ سازمان مستقلی وجود ندارد؛ کنش جمعی تقریباً ناممکن است.
  ۳-۴  ضعیف: بسیج پراکنده و به‌آسانی سرکوب‌شونده.
  ۵-۶  متوسط: حیات انجمنی واقعی و بسیج مؤثر دوره‌ای.
  ۷-۸  قوی: نهادهای مدنی متراکم که به‌طور منظم دولت را محدود می‌کنند.
  ۹-۱۰ مسلط: جامعه به‌طور گسترده کنش دولت را شکل می‌دهد و مهار می‌کند.

راهنمای بی‌طرفی:
- هر دوره را بر پایه‌ی شرایط خودش داوری کنید؛ فرض نکنید که کشور به سوی آزادی،
  خودکامگی یا گوشه‌ای خاص از این فضا میل می‌کند.
- پیش از تعیین عدد، شواهد موافق و مخالف یک تغییر را بسنجید.
- از حال‌گرایی بپرهیزید: بر پایه‌ی معیارها و اطلاعات همان دوره امتیاز دهید، نه
  بر پایه‌ی آنچه بعدها رخ داد.
- این دو محور مستقل‌اند: یک دولت قوی می‌تواند با جامعه‌ای قوی یا ضعیف هم‌زیستی
  داشته باشد. آن‌ها را جداگانه امتیاز دهید.""",
    "es": """\
Utilice este baremo fijo de 0 a 10 para que los valores sean comparables entre
periodos y países.

PODER DEL ESTADO — la capacidad del Estado para imponer su voluntad, administrar
el territorio, recaudar impuestos y proyectar autoridad:
  0-2  colapsado / inexistente: no hay autoridad central efectiva.
  3-4  débil: alcance limitado, control disputado, depende de poderes locales.
  5-6  moderado: burocracia y ejército funcionales, con alcance real pero acotado.
  7-8  fuerte: administración omnipresente, coerción eficaz y capacidad de recaudación.
  9-10 abrumador: penetración casi total de la sociedad; poco que no pueda imponer.

PODER DE LA SOCIEDAD — la capacidad de la sociedad civil para organizarse,
movilizarse, exigir cuentas al Estado y resistir la dominación (normas,
asociaciones, prensa, protesta, instituciones independientes):
  0-2  atomizada: sin organización autónoma; la acción colectiva es casi imposible.
  3-4  débil: movilización esporádica y fácilmente reprimida.
  5-6  moderada: vida asociativa real y movilización eficaz de forma periódica.
  7-8  fuerte: instituciones cívicas densas que limitan al Estado con regularidad.
  9-10 dominante: la sociedad moldea y controla ampliamente la acción del Estado.

Pautas de objetividad:
- Juzgue cada periodo en sus propios términos; no suponga que el país tiende
  hacia la libertad, la autocracia o algún rincón concreto del espacio.
- Sopese las pruebas a favor y en contra de un cambio antes de fijar una cifra.
- Evite el presentismo: puntúe según las normas e información de la época, no
  según cómo resultaron las cosas después.
- Estos dos ejes son independientes: un Estado fuerte puede coexistir con una
  sociedad fuerte o débil. Puntúelos por separado.""",
    "ar": """\
استخدم هذا المقياس الثابت من 0 إلى 10 لكي تكون القيم قابلة للمقارنة عبر الفترات
والدول.

قوة الدولة — قدرة الدولة على فرض إرادتها وإدارة الإقليم وجباية الضرائب وبسط
سلطتها:
  0-2  منهارة / غير موجودة: لا سلطة مركزية فعّالة.
  3-4  ضعيفة: نطاق محدود، وسيطرة متنازع عليها، وتعتمد على قوى محلية.
  5-6  متوسطة: بيروقراطية وجيش يعملان بنطاق حقيقي لكنه محدود.
  7-8  قوية: إدارة شاملة، وقدرة فعّالة على القمع وتحصيل الإيرادات.
  9-10 طاغية: اختراق شبه كامل للمجتمع؛ قلّ ما لا تستطيع فرضه.

قوة المجتمع — قدرة المجتمع المدني على التنظيم والتعبئة ومساءلة الدولة ومقاومة
الهيمنة (الأعراف، الجمعيات، الصحافة، الاحتجاج، المؤسسات المستقلة):
  0-2  مفكَّك: لا تنظيم مستقل؛ العمل الجماعي شبه مستحيل.
  3-4  ضعيف: تعبئة متفرقة يسهل قمعها.
  5-6  متوسط: حياة جمعياتية حقيقية وتعبئة فعّالة بين حين وآخر.
  7-8  قوي: مؤسسات مدنية كثيفة تقيّد الدولة بانتظام.
  9-10 مهيمن: المجتمع يشكّل عمل الدولة ويكبحه على نطاق واسع.

إرشادات الموضوعية:
- احكم على كل فترة بمعاييرها الخاصة؛ لا تفترض أن الدولة تتجه نحو الحرية أو
  الاستبداد أو أي ركن بعينه من الفضاء.
- زِن الأدلة المؤيِّدة والمعارِضة للتغيّر قبل أن تستقر على رقم.
- تجنّب إسقاط الحاضر: قيّم وفق معايير ومعلومات تلك الفترة، لا وفق ما آلت إليه
  الأمور لاحقًا.
- هذان المحوران مستقلان: يمكن أن تتعايش دولة قوية مع مجتمع قوي أو ضعيف. قيّمهما
  بشكل منفصل.""",
}

_ET_I18N = {
    "fr": """\
En vous appuyant sur le cadre d'analyse de Daron Acemoğlu et James A. Robinson
dans *The Narrow Corridor: States, Societies, and the Fate of Liberty*,
identifiez les grands événements et tendances historiques en {country} durant
{period_text} qui ont matériellement affecté SOIT le pouvoir de l'État SOIT le
pouvoir de la société civile.

Soyez concret et précis pour {period_text}. Distinguez les tendances lentes
(institutionnelles, économiques, démographiques) des événements ponctuels. Pour
chaque élément, indiquez brièvement s'il a renforcé ou affaibli l'État, la
société, ou les deux.

Répondez par deux courtes listes à puces :

Tendances :
- ...

Événements :
- ...""",
    "zh": """\
参照达龙·阿西莫格鲁（Daron Acemoğlu）与詹姆斯·A·罗宾逊（James A. Robinson）在
《狭窄的走廊：国家、社会与自由的命运》(The Narrow Corridor) 中的分析框架，指出
{country} 在 {period_text} 期间对国家权力或公民社会权力产生实质性影响的重大
历史事件与趋势。

请针对 {period_text} 给出具体而明确的内容。区分缓慢演变的趋势（制度、经济、
人口）与离散的事件。对每一项，简要说明它是增强还是削弱了国家、社会，或两者。

请用两个简短的项目符号列表作答：

趋势：
- ...

事件：
- ...""",
    "fa": """\
با در نظر گرفتن چارچوب دارون عجم‌اوغلو (Daron Acemoğlu) و جیمز ای. رابینسون
(James A. Robinson) در کتاب *The Narrow Corridor: States, Societies, and the
Fate of Liberty*، رویدادها و روندهای مهم تاریخی در {country} طی {period_text} را
شناسایی کنید که به‌طور اساسی یا بر قدرت دولت یا بر قدرت جامعه‌ی مدنی اثر
گذاشته‌اند.

مشخص و دقیق درباره‌ی {period_text} پاسخ دهید. روندهای کند (نهادی، اقتصادی،
جمعیتی) را از رویدادهای مجزا تفکیک کنید. برای هر مورد، به‌اختصار بگویید که آیا
دولت، جامعه یا هر دو را تقویت یا تضعیف کرده است.

با دو فهرست کوتاه گلوله‌ای پاسخ دهید:

روندها:
- ...

رویدادها:
- ...""",
    "es": """\
Considerando el marco de Daron Acemoğlu y James A. Robinson en *The Narrow
Corridor: States, Societies, and the Fate of Liberty*, identifique los
principales acontecimientos y tendencias históricas en {country} durante
{period_text} que afectaron materialmente O BIEN al poder del Estado O BIEN al
poder de la sociedad civil.

Sea concreto y específico para {period_text}. Distinga las tendencias lentas
(institucionales, económicas, demográficas) de los acontecimientos puntuales.
Para cada elemento, indique brevemente si fortaleció o debilitó al Estado, a la
sociedad, o a ambos.

Responda con dos listas breves con viñetas:

Tendencias:
- ...

Acontecimientos:
- ...""",
    "ar": """\
بالنظر إلى إطار دارون عجم أوغلو (Daron Acemoğlu) وجيمس أ. روبنسون (James A.
Robinson) في كتاب *The Narrow Corridor: States, Societies, and the Fate of
Liberty*، حدّد أبرز الأحداث والاتجاهات التاريخية في {country} خلال {period_text}
التي أثّرت تأثيرًا جوهريًا إمّا في قوة الدولة وإمّا في قوة المجتمع المدني.

كن محدَّدًا ودقيقًا بشأن {period_text}. ميّز بين الاتجاهات البطيئة (المؤسسية
والاقتصادية والديموغرافية) والأحداث المنفصلة. ولكل بند، بيّن باختصار ما إذا كان
قد عزّز أو أضعف الدولة أو المجتمع أو كليهما.

أجب بقائمتين قصيرتين بنقاط:

الاتجاهات:
- ...

الأحداث:
- ...""",
}

_FRAMING_I18N = {
    "fr": """\
Vous placez le pays {country} dans l'espace 2D de *The Narrow Corridor*
d'Acemoğlu et Robinson : l'axe des x est le pouvoir de la société civile et
l'axe des y est le pouvoir de l'État. Nous traçons la trajectoire de
{start_year} à {end_year}.

{rubric}""",
    "zh": """\
你正在把 {country} 这个国家置于阿西莫格鲁与罗宾逊《狭窄的走廊》的二维空间中：
x 轴是公民社会的权力，y 轴是国家的权力。我们正在描绘从 {start_year} 到
{end_year} 的轨迹。

{rubric}""",
    "fa": """\
شما کشور {country} را در فضای دوبعدی کتاب *The Narrow Corridor* اثر عجم‌اوغلو و
رابینسون قرار می‌دهید: محور x قدرت جامعه‌ی مدنی و محور y قدرت دولت است. ما مسیر
را از {start_year} تا {end_year} ترسیم می‌کنیم.

{rubric}""",
    "es": """\
Está situando al país de {country} en el espacio 2D de *The Narrow Corridor* de
Acemoğlu y Robinson: el eje x es el poder de la sociedad civil y el eje y es el
poder del Estado. Estamos trazando la trayectoria desde {start_year} hasta
{end_year}.

{rubric}""",
    "ar": """\
أنت تضع دولة {country} في الفضاء ثنائي الأبعاد لكتاب *The Narrow Corridor*
لعجم أوغلو وروبنسون: المحور الأفقي (x) هو قوة المجتمع المدني، والمحور الرأسي (y)
هو قوة الدولة. نحن نرسم المسار من {start_year} إلى {end_year}.

{rubric}""",
}

_BOOTSTRAP_I18N = {
    "fr": """\
{framing}

Il s'agit de la PREMIÈRE période de la trajectoire : {period_text}. Établissez
le point de départ. Estimez le pouvoir absolu de la société civile et celui de
l'État en {country} durant {period_text} à l'aide du barème ci-dessus. Comme il
n'y a pas de période antérieure, indiquez les deux valeurs de changement comme 0.0.

Renvoyez un objet JSON comportant exactement ces champs :
- society_power (float, 0-10)
- state_power (float, 0-10)
- society_change (float, 0.0)
- state_change (float, 0.0)
- key_event (string, <= ~10 mots : la caractéristique la plus déterminante de cette période)
- reasoning (string, 1-2 phrases justifiant les deux valeurs de pouvoir)""",
    "zh": """\
{framing}

这是轨迹的第一个时期：{period_text}。请确立起点。使用上述评分标准，估计
{country} 在 {period_text} 期间公民社会与国家的绝对权力。由于没有前一个时期，
请将两个变化值都记为 0.0。

请返回一个 JSON 对象，且恰好包含以下字段：
- society_power (float, 0-10)
- state_power (float, 0-10)
- society_change (float, 0.0)
- state_change (float, 0.0)
- key_event (string，<= 约 10 个词：该时期最具决定性的特征)
- reasoning (string，1-2 句话，说明这两个权力数值的理由)""",
    "fa": """\
{framing}

این نخستین دوره‌ی مسیر است: {period_text}. نقطه‌ی آغاز را تعیین کنید. با استفاده
از معیار بالا، قدرت مطلق جامعه‌ی مدنی و دولت را در {country} طی {period_text}
برآورد کنید. چون دوره‌ی پیشینی وجود ندارد، هر دو مقدار تغییر را 0.0 گزارش کنید.

یک شیء JSON با دقیقاً همین فیلدها بازگردانید:
- society_power (float, 0-10)
- state_power (float, 0-10)
- society_change (float, 0.0)
- state_change (float, 0.0)
- key_event (string، حداکثر حدود ۱۰ کلمه: تعیین‌کننده‌ترین ویژگی این دوره)
- reasoning (string، ۱ تا ۲ جمله در توجیه دو مقدار قدرت)""",
    "es": """\
{framing}

Este es el PRIMER periodo de la trayectoria: {period_text}. Establezca el punto
de partida. Estime el poder absoluto de la sociedad civil y del Estado en
{country} durante {period_text} usando el baremo anterior. Como no hay periodo
anterior, informe ambos valores de cambio como 0.0.

Devuelva un objeto JSON con exactamente estos campos:
- society_power (float, 0-10)
- state_power (float, 0-10)
- society_change (float, 0.0)
- state_change (float, 0.0)
- key_event (string, <= ~10 palabras: el rasgo más definitorio de este periodo)
- reasoning (string, 1-2 frases que justifiquen los dos valores de poder)""",
    "ar": """\
{framing}

هذه هي الفترة الأولى من المسار: {period_text}. حدِّد نقطة البداية. قدّر القوة
المطلقة للمجتمع المدني وللدولة في {country} خلال {period_text} باستخدام المقياس
أعلاه. وبما أنه لا توجد فترة سابقة، فأورِد كلتا قيمتي التغيّر بوصفهما 0.0.

أعِد كائن JSON يحتوي على هذه الحقول بالضبط:
- society_power (float, 0-10)
- state_power (float, 0-10)
- society_change (float, 0.0)
- state_change (float, 0.0)
- key_event (string، بحد أقصى نحو 10 كلمات: أبرز سمة مميِّزة لهذه الفترة)
- reasoning (string، جملة أو جملتان لتبرير قيمتي القوة)""",
}

_SCORE_I18N = {
    "fr": """\
{framing}

Notez la période {period_text}, en vous appuyant sur la trajectoire établie.
Partez de la position de {country} à la fin de {previous_period_text}, puis
appliquez les changements induits par les événements et tendances ci-dessous.
Indiquez à la fois le changement par axe et les valeurs absolues résultantes
(ancrées au barème, et non seulement au point précédent). Une période avec peu
de changement réel devrait montrer des changements proches de 0.0.

Événements et tendances historiques en {period_text} :
{events_trends_text}

Trajectoire jusqu'ici (période : <society_power, state_power>) :
{previous_scores_text}

Renvoyez un objet JSON comportant exactement ces champs :
- society_power (float, 0-10) : pouvoir absolu de la société à la fin de {period_text}
- state_power (float, 0-10) : pouvoir absolu de l'État à la fin de {period_text}
- society_change (float) : changement de society_power par rapport à {previous_period_text}
- state_change (float) : changement de state_power par rapport à {previous_period_text}
- key_event (string, <= ~10 mots : l'événement/la tendance déterminant(e) du changement)
- reasoning (string, 1-2 phrases justifiant les valeurs)""",
    "zh": """\
{framing}

请为 {period_text} 时期评分，在既有轨迹的基础上进行。从 {country} 在
{previous_period_text} 末的位置出发，然后应用下述事件与趋势所带来的变化。请同时
给出每个维度的变化量与由此得到的绝对数值（以评分标准为锚，而不仅仅相对于前一个
点）。若某时期几乎没有真实变化，其变化量应接近 0.0。

{period_text} 的历史事件与趋势：
{events_trends_text}

迄今为止的轨迹（时期：<society_power, state_power>）：
{previous_scores_text}

请返回一个 JSON 对象，且恰好包含以下字段：
- society_power (float, 0-10)：{period_text} 末公民社会的绝对权力
- state_power (float, 0-10)：{period_text} 末国家的绝对权力
- society_change (float)：相对于 {previous_period_text} 的 society_power 变化
- state_change (float)：相对于 {previous_period_text} 的 state_power 变化
- key_event (string，<= 约 10 个词：驱动此次变化的决定性事件／趋势)
- reasoning (string，1-2 句话，说明数值的理由)""",
    "fa": """\
{framing}

دوره‌ی {period_text} را بر پایه‌ی مسیر تثبیت‌شده امتیاز دهید. از جایگاه {country}
در پایان {previous_period_text} آغاز کنید، سپس تغییرهای ناشی از رویدادها و
روندهای زیر را اعمال کنید. هم تغییر هر محور و هم مقادیر مطلق حاصل را گزارش کنید
(لنگرانداخته به معیار، نه صرفاً نسبت به نقطه‌ی پیشین). دوره‌ای با تغییر واقعی
اندک باید تغییرهایی نزدیک به 0.0 نشان دهد.

رویدادها و روندهای تاریخی در {period_text}:
{events_trends_text}

مسیر تا کنون (دوره: <society_power, state_power>):
{previous_scores_text}

یک شیء JSON با دقیقاً همین فیلدها بازگردانید:
- society_power (float, 0-10): قدرت مطلق جامعه در پایان {period_text}
- state_power (float, 0-10): قدرت مطلق دولت در پایان {period_text}
- society_change (float): تغییر society_power نسبت به {previous_period_text}
- state_change (float): تغییر state_power نسبت به {previous_period_text}
- key_event (string، حداکثر حدود ۱۰ کلمه: رویداد/روند تعیین‌کننده‌ی این تغییر)
- reasoning (string، ۱ تا ۲ جمله در توجیه مقادیر)""",
    "es": """\
{framing}

Puntúe el periodo {period_text}, partiendo de la trayectoria establecida.
Comience desde donde estaba {country} al final de {previous_period_text}, luego
aplique los cambios que implican los acontecimientos y tendencias siguientes.
Informe tanto el cambio por eje como los valores absolutos resultantes (anclados
al baremo, no solo al punto anterior). Un periodo con poco cambio real debería
mostrar cambios cercanos a 0.0.

Acontecimientos y tendencias históricas en {period_text}:
{events_trends_text}

Trayectoria hasta ahora (periodo: <society_power, state_power>):
{previous_scores_text}

Devuelva un objeto JSON con exactamente estos campos:
- society_power (float, 0-10): poder absoluto de la sociedad al final de {period_text}
- state_power (float, 0-10): poder absoluto del Estado al final de {period_text}
- society_change (float): cambio de society_power respecto a {previous_period_text}
- state_change (float): cambio de state_power respecto a {previous_period_text}
- key_event (string, <= ~10 palabras: el acontecimiento/tendencia determinante del cambio)
- reasoning (string, 1-2 frases que justifiquen los valores)""",
    "ar": """\
{framing}

قيّم الفترة {period_text} بالبناء على المسار المُثبَت. ابدأ من موضع {country} في
نهاية {previous_period_text}، ثم طبّق التغيّرات التي تقتضيها الأحداث والاتجاهات
أدناه. أورِد كلًّا من التغيّر لكل محور والقيم المطلقة الناتجة (مرتكِزة إلى
المقياس، لا إلى النقطة السابقة فحسب). الفترة ذات التغيّر الفعلي الطفيف ينبغي أن
تُظهر تغيّرات قريبة من 0.0.

الأحداث والاتجاهات التاريخية في {period_text}:
{events_trends_text}

المسار حتى الآن (الفترة: <society_power, state_power>):
{previous_scores_text}

أعِد كائن JSON يحتوي على هذه الحقول بالضبط:
- society_power (float, 0-10): القوة المطلقة للمجتمع في نهاية {period_text}
- state_power (float, 0-10): القوة المطلقة للدولة في نهاية {period_text}
- society_change (float): تغيّر society_power مقارنةً بـ {previous_period_text}
- state_change (float): تغيّر state_power مقارنةً بـ {previous_period_text}
- key_event (string، بحد أقصى نحو 10 كلمات: الحدث/الاتجاه الحاسم وراء التغيّر)
- reasoning (string، جملة أو جملتان لتبرير القيم)""",
}
