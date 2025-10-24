# app.py
import os, re, time, traceback, random
from typing import Tuple, Optional, List, Callable, Any
import gradio as gr

# ================= OpenAI client =================
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")

def _client_or_error() -> Tuple[Optional["OpenAI"], Optional[str]]:
    if OpenAI is None:
        return None, "OpenAI SDK not installed. Add openai>=1.50.0 to requirements.txt"
    if not os.getenv("OPENAI_API_KEY"):
        return None, "Missing OPENAI_API_KEY environment variable"
    try:
        return OpenAI(), None
    except Exception as e:
        return None, f"Failed to initialize OpenAI client: {e}"

# ================= helpers =================
def _split_lines_keep_nonempty(text: str) -> List[str]:
    return [ln for ln in (l.strip() for l in text.splitlines()) if ln]

def _parse_titles_unique_numbered(text: str) -> List[str]:
    seen = set()
    out = []
    for raw in _split_lines_keep_nonempty(text):
        cleaned = re.sub(r"^\s*(?:\d+\s*[.)]|[-*•]+)\s*", "", raw, count=1).strip()
        if cleaned:
            key = cleaned.lower()
            if key not in seen:
                seen.add(key)
                out.append(cleaned)
    return [f"{i + 1}. {t}" for i, t in enumerate(out)]

def _strip_markdown(md: str) -> str:
    if not md:
        return ""
    txt = re.sub(r"[*_`]{1,2}", "", md)
    txt = re.sub(r"^•\s*", "- ", txt, flags=re.MULTILINE)
    txt = re.sub(r"^#+\s*", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def _first_bullet_enforcer(md: str) -> str:
    def _fix(section: str, text: str) -> str:
        pattern = rf"(\*\*{re.escape(section)}:\*\*)"
        text = re.sub(pattern + r"\s*", r"\1\n", text, flags=re.IGNORECASE)
        text = re.sub(rf"(\*\*{re.escape(section)}:\*\*\n)(?!•)", r"\1", text, flags=re.IGNORECASE)
        return text
    md = _fix("Ingredients", md)
    md = _fix("Storage", md)
    return md

def _safe_backoff(fn: Callable[[], Any], retries: int = 3, base: float = 0.8) -> Any:
    for attempt in range(retries):
        try:
            return fn()
        except Exception:
            if attempt == retries - 1:
                raise
            sleep_s = base * (2 ** attempt) + random.random() * 0.25
            time.sleep(sleep_s)

# ================= prompts =================
LIST_SYSTEM = (
    "You are ChatGPT. When asked for recipe titles, respond with titles only, one per line. "
    "No commentary or numbering unless explicitly requested. Titles must be realistic, literal recipes."
)
LIST_USER_TEMPLATE = (
    "Generate exactly {count} recipe titles for the subje


britt@Skittles MINGW64 ~/Documents/RecipeCards (main)
$ git add app.py
# create app.py in the current folder
cat > app.py << 'PY'
# app.py
import os, re, time, traceback, random
from typing import Tuple, Optional, List, Callable, Any
import gradio as gr

# ================= OpenAI client =================
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")

def _client_or_error() -> Tuple[Optional["OpenAI"], Optional[str]]:
    if OpenAI is None:
        return None, "OpenAI SDK not installed. Add openai>=1.50.0 to requirements.txt"
    if not os.getenv("OPENAI_API_KEY"):
        return None, "Missing OPENAI_API_KEY environment variable"
    try:
        return OpenAI(), None
    except Exception as e:
        return None, f"Failed to initialize OpenAI client: {e}"

# ================= helpers =================
def _split_lines_keep_nonempty(text: str) -> List[str]:
    return [ln for ln in (l.strip() for l in text.splitlines()) if ln]

def _parse_titles_unique_numbered(text: str) -> List[str]:
    seen = set()
    out = []
    for raw in _split_lines_keep_nonempty(text):
        cleaned = re.sub(r"^\s*(?:\d+\s*[.)]|[-*•]+)\s*", "", raw, count=1).strip()
        if cleaned:
            key = cleaned.lower()
            if key not in seen:
                seen.add(key)
                out.append(cleaned)
    return [f"{i + 1}. {t}" for i, t in enumerate(out)]

def _strip_markdown(md: str) -> str:
    if not md:
        return ""
    txt = re.sub(r"[*_`]{1,2}", "", md)
    txt = re.sub(r"^•\s*", "- ", txt, flags=re.MULTILINE)
    txt = re.sub(r"^#+\s*", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def _first_bullet_enforcer(md: str) -> str:
    def _fix(section: str, text: str) -> str:
        pattern = rf"(\*\*{re.escape(section)}:\*\*)"
        text = re.sub(pattern + r"\s*", r"\1\n", text, flags=re.IGNORECASE)
        text = re.sub(rf"(\*\*{re.escape(section)}:\*\*\n)(?!•)", r"\1", text, flags=re.IGNORECASE)
        return text
    md = _fix("Ingredients", md)
    md = _fix("Storage", md)
    return md

def _safe_backoff(fn: Callable[[], Any], retries: int = 3, base: float = 0.8) -> Any:
    for attempt in range(retries):
        try:
            return fn()
        except Exception:
            if attempt == retries - 1:
                raise
            sleep_s = base * (2 ** attempt) + random.random() * 0.25
            time.sleep(sleep_s)

# ================= prompts =================
LIST_SYSTEM = (
    "You are ChatGPT. When asked for recipe titles, respond with titles only, one per line. "
    "No commentary or numbering unless explicitly requested. Titles must be realistic, literal recipes."
)
LIST_USER_TEMPLATE = (
    "Generate exactly {count} recipe titles for the subject: {subject}.\n"
    "Return titles only, one per line."
)

RECIPE_SYSTEM_STANDARD = (
    "Output a single recipe card using the exact markdown layout below. "
    "Each section must begin on its own line, with the first bullet appearing directly under the 'Ingredients:' "
    "and 'Storage:' headers. Include a complete, realistic ingredient list. Preserve bold labels and spacing exactly."
)

RECIPE_TEMPLATE_STANDARD = """**{title}**

A concise two sentence summary of the dish.

**Yields:** 1 serving
**Prep time:** 10 minutes
**Cook time:** 10 minutes

**Ingredients:**
• ingredient 1
• ingredient 2
• ingredient 3
• ingredient 4
• ingredient 5
• ingredient 6

**Directions:**
Write short, clear steps in a single paragraph.

**Storage:**
• Refrigerate up to 3 days.
• Freeze up to 3 months.

**Serving size:** 1 serving ~6 oz | 1 cup

**Nutritional Facts per Serving:**
Calories X | Protein X g | Total Fat X g (Y g sat | 0 g trans) | Carbohydrates X g | Fiber X g | Sugar X g | Sodium X mg
"""

RECIPE_USER_TEMPLATE_STANDARD = (
    "Write a recipe card titled '{title}' using the exact markdown structure shown below. "
    "Ensure the first bullet under 'Ingredients:' and 'Storage:' begins on the next line. "
    "Include a complete ingredient list with no missing items.\n\n" + RECIPE_TEMPLATE_STANDARD
)

RECIPE_SYSTEM_BARIATRIC = (
    "You are generating a recipe card optimized for bariatric patients following a four stage program:\n"
    "Stage 1: Clear liquids and protein supplements\n"
    "Stage 2: Modified liquids strained or blended\n"
    "Stage 3: Soft and moist solids\n"
    "Stage 4: Regular lifelong bariatric diet solids\n"
    "Select the appropriate stage s for the recipe based on texture and ingredients. "
    "Prioritize lean protein, moderate healthy fats, limited added sugars, modest portions, and stage appropriate textures. "
    "Do not mention any program or hospital name on the card. "
    "The output must follow the same markdown structure as the standard recipe including bullet placement rules."
)

RECIPE_TEMPLATE_BARIATRIC = """**{title}**
**Bariatric Stage(s):** <choose from Stage 1, Stage 2, Stage 3, Stage 4>

A concise two sentence summary tailored to bariatric needs.

**Yields:** 1 serving
**Prep time:** 10 minutes
**Cook time:** 10 minutes

**Ingredients:**
• ingredient 1
• ingredient 2
• ingredient 3
• ingredient 4
• ingredient 5
• ingredient 6

**Directions:**
Write short clear sentences appropriate to the selected stage s.

**Substitutions Bariatric:**
• substitution 1
• substitution 2
• substitution 3

**Storage:**
• Refrigerate up to 3 days.
• Freeze up to 3 months.

**Serving size:** 1 serving ~4 to 6 oz

**Nutritional Facts per Serving:**
Calories X | Protein X g | Fat X g (Y g sat | 0 g trans) | Carbohydrates X g | Fiber X g | Sugar X g | Sodium X mg
"""

RECIPE_USER_TEMPLATE_BARIATRIC = (
    "Write a bariatric recipe titled '{title}' in the exact markdown structure below. "
    "Each section must start on a new line with bullets directly beneath 'Ingredients:' and 'Storage:'. "
    "Ensure the ingredient list is fully populated with no missing bullets. Do not mention any hospital or program names.\n\n"
    + RECIPE_TEMPLATE_BARIATRIC
)

# ================= image generator =================
def chatgpt_generate_image(title: str) -> Optional[str]:
    client, err = _client_or_error()
    if err:
        return None
    prompt = f"Professional plating photo of {title}, natural lighting, clean background."
    try:
        def _call():
            return client.images.generate(model=OPENAI_IMAGE_MODEL, prompt=prompt, size="1024x1024")
        img = _safe_backoff(_call, retries=2)
        return img.data[0].url if img and img.data else None
    except Exception:
        traceback.print_exc()
        return None

# ================= chat completions =================
def _chat(model: str, system_prompt: str, user_prompt: str) -> str:
    client, err = _client_or_error()
    if err:
        raise RuntimeError(err)
    def _call():
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()
    try:
        return _safe_backoff(_call, retries=3)
    except Exception as e:
        raise RuntimeError(f"{type(e).__name__}: {e}")

def chatgpt_generate_titles(subject: str, count: int) -> List[str]:
    text = _chat(OPENAI_MODEL, LIST_SYSTEM, LIST_USER_TEMPLATE.format(subject=subject, count=count))
    if not text.strip():
        raise RuntimeError("Empty response for titles")
    return _parse_titles_unique_numbered(text)

def chatgpt_generate_recipe(title: str, bariatric: bool = False) -> str:
    if bariatric:
        system_msg = RECIPE_SYSTEM_BARIATRIC
        user_msg = RECIPE_USER_TEMPLATE_BARIATRIC.format(title=title)
    else:
        system_msg = RECIPE_SYSTEM_STANDARD
        user_msg = RECIPE_USER_TEMPLATE_STANDARD.format(title=title)

    recipe_md = _chat(OPENAI_MODEL, system_msg, user_msg)
    recipe_md = _first_bullet_enforcer(recipe_md)

    image_url = chatgpt_generate_image(title)
    if image_url:
        recipe_md = (
            f'<div class="fade-in"><img src="{image_url}" alt="{title}" '
            f'style="max-width:100%;border-radius:12px;margin-bottom:15px;"></div>\n\n'
            + recipe_md
        )
    return recipe_md

# ================= UI =================
def build_ui():
    _, ready_err = _client_or_error()
    is_ready = ready_err is None
    initial_status = f"**Error:** {ready_err}" if ready_err else ""

    css = """
    .fade-in { opacity: 0; animation: fadeInEffect 0.9s ease-in forwards; }
    @keyframes fadeInEffect {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .loading { font-size: 0.9rem; opacity: .85; }

    .linklike button, .linklike .gr-button {
        background: transparent !important;
        color: #2563eb !important;
        text-decoration: underline;
        border: none !important;
        box-shadow: none !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    .subject-row { display: flex; align-items: center; gap: 12px; }
    .subject-row .right { flex: 0 0 auto; }
    .subject-row .badge {
        display: inline-block; padding: 4px 8px; border-radius: 9999px;
        font-size: 12px; line-height: 1; background: #eef2ff; color: #3730a3; font-weight: 600;
    }

    #num_slider label { display: none !important; }
    #titles_label { white-space: nowrap; font-weight: 600; }

    #num_slider input[type="number"],
    #num_slider .input-number,
    #num_slider .wrap .controls,
    #num_slider .wrap .number,
    #num_slider .min,
    #num_slider .max,
    #num_slider button[aria-label],
    #num_slider svg {
        display: none !important;
    }
    """

    with gr.Blocks(title="Britt's Bistro Cafe - Meal Planning", css=css, theme=gr.themes.Soft()) as demo:
        gr.Markdown("## Britt's Bistro Cafe - Meal Planning")
        status_msg = gr.Markdown(value=initial_status, visible=bool(initial_status))

        with gr.Tabs(selected="List Generator") as tabs:
            with gr.Tab("List Generator"):
                gr.Markdown("### List Generator")

                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Row(elem_classes="subject-row"):
                            subject = gr.Textbox(label="Subject", value="Peach Cobbler")
                            gr.HTML('<div class="right"><span class="badge">1000</span></div>')

                with gr.Row():
                    with gr.Column(scale=0, min_width=160):
                        gr.HTML('<div id="titles_label">How many titles?</div>')
                    with gr.Column(scale=4):
                        num_slider = gr.Slider(1, 1000, value=5, step=1, label="", interactive=True, elem_id="num_slider")

                with gr.Row():
                    generate_btn = gr.Button("Generate Titles", variant="primary", interactive=is_ready)
                    recipe_btn = gr.Button("Recipe", variant="secondary", elem_classes="linklike", interactive=False)

                bariatric_enable = gr.Checkbox(label="Enable Bariatric generation", value=False)

                table = gr.Dataframe(headers=["#", "Title"], datatype=["number", "str"], interactive=False, wrap=True)
                copy_titles_box = gr.Textbox(lines=10, interactive=False, show_copy_button=True)
                raw_titles_state = gr.State([])
                selected_title_state = gr.State(None)

            with gr.Tab("Recipe Generator"):
                recipe_md = gr.Markdown(value="Select a title and click Recipe.")
                recipe_copy_box = gr.Textbox(lines=18, interactive=False, show_copy_button=True)

            with gr.Tab("Bariatric Recipe Generator"):
                bari_loading = gr.Markdown(visible=False)
                bari_recipe_md = gr.Markdown(value="Enable Bariatric and click Recipe to generate here.")
                bari_recipe_copy_box = gr.Textbox(lines=18, interactive=False, show_copy_button=True)

        def _run_generate(subject, num):
            client, err = _client_or_error()
            if err:
                msg = f"[ERROR] {err}"
                return [], [], None, gr.update(value=msg), gr.update(value=f"**Error:** {msg}", visible=True), gr.update(interactive=False)
            try:
                titles = chatgpt_generate_titles(subject, int(num))
                df = [[i + 1, re.sub(r'^\d+\.\s*', '', t)] for i, t in enumerate(titles)]
                joined = "\n".join(titles)
                default_sel = re.sub(r"^\d+\.\s*", "", titles[0]) if titles else None

                notice = ""
                if len(titles) < int(num):
                    notice = f"Requested {int(num)} titles. Generated {len(titles)} without duplicates."

                return (
                    df,
                    titles,
                    default_sel,
                    gr.update(value=joined),
                    gr.update(value=(f"**Notice:** {notice}" if notice else ""), visible=bool(notice)),
                    gr.update(interactive=bool(titles)),
                )
            except Exception as e:
                err_text = f"[ERROR] {type(e).__name__}: {e}"
                return [], [], None, gr.update(value=err_text), gr.update(value=f"**Error:** {err_text}", visible=True), gr.update(interactive=False)

        generate_btn.click(
            _run_generate,
            inputs=[subject, num_slider],
            outputs=[table, raw_titles_state, selected_title_state, copy_titles_box, status_msg, recipe_btn],
        )

        def _on_select(evt: gr.SelectData, raw_titles):
            if evt is None or raw_titles is None:
                return gr.update()
            ri = evt.index
            idx = ri[0] if isinstance(ri, list) else ri
            if isinstance(idx, int) and 0 <= idx < len(raw_titles):
                return re.sub(r"^\d+\.\s*", "", raw_titles[idx])
            return gr.update()

        table.select(_on_select, inputs=[raw_titles_state], outputs=[selected_title_state])

        def _generate_recipe(selected_title, raw_titles, bariatric_enabled):
            if not raw_titles:
                yield (
                    gr.update(value="No titles available. Generate titles first."),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(selected="List Generator"),
                    gr.update(value=""),
                ); return

            title = selected_title or (re.sub(r"^\d+\.\s*", "", raw_titles[0]) if raw_titles else None)
            if not title:
                yield (
                    gr.update(value="No title selected."),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(selected="List Generator"),
                    gr.update(value=""),
                ); return

            js_scroll = "<script>window.scrollTo({top:0,behavior:'smooth'});</script>"

            if bariatric_enabled:
                yield (
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value="### Generating bariatric recipe…", visible=True),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(selected="Bariatric Recipe Generator"),
                    gr.update(value=js_scroll),
                )
                try:
                    recipe_bari_md = chatgpt_generate_recipe(title, bariatric=True)
                except Exception as e:
                    recipe_bari_md = f"**Error:** {type(e).__name__}: {e}"
                yield (
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(visible=False),
                    gr.update(value=recipe_bari_md),
                    gr.update(value=_strip_markdown(recipe_bari_md)),
                    gr.update(selected="Bariatric Recipe Generator"),
                    gr.update(value=js_scroll),
                )
            else:
                yield (
                    gr.update(value="### Generating recipe…", visible=True),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(selected="Recipe Generator"),
                    gr.update(value=js_scroll),
                )
                try:
                    recipe_std_md = chatgpt_generate_recipe(title, bariatric=False)
                except Exception as e:
                    recipe_std_md = f"**Error:** {type(e).__name__}: {e}"
                yield (
                    gr.update(value=recipe_std_md),
                    gr.update(value=_strip_markdown(recipe_std_md)),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(selected="Recipe Generator"),
                    gr.update(value=js_scroll),
                )

        recipe_btn.click(
            _generate_recipe,
            inputs=[selected_title_state, raw_titles_state, bariatric_enable],
            outputs=[recipe_md, recipe_copy_box, bari_loading, bari_recipe_md, bari_recipe_copy_box, tabs, gr.HTML("")],
        )

    return demo

# ================= launch =================
if __name__ == "__main__":
    demo = build_ui()
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        inbrowser=True,
        share=False,
    )
