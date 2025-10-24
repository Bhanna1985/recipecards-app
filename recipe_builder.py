import os, re
from pathlib import Path
import pandas as pd
from docxtpl import DocxTemplate

# ==============================
# CONFIG
# ==============================
INPUT_CSV = "master_recipes.csv"
TEMPLATE_FILE = "recipe_template.docx"   # Word template with {{placeholders}}
OUTPUT_DIR = Path("recipes_docx")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_CANVA = "recipes_canva.csv"

# Threshold for when to trigger overflow
OVERFLOW_THRESHOLD = 1800  # total characters of ingredients + directions


# ==============================
# HELPERS
# ==============================
def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def needs_overflow(ingredients: str, directions: str) -> bool:
    """Return True if recipe text is too long for one page."""
    total_len = len(str(ingredients)) + len(str(directions))
    return total_len > OVERFLOW_THRESHOLD


# ==============================
# MAIN BUILDER
# ==============================
def build_outputs(df):
    canva_rows = []

    for i, (_, row) in enumerate(df.iterrows()):
        title = str(row["Title"])
        servings = row.get("Servings", "")
        prep_time = row.get("PrepTime", "")
        cook_time = row.get("CookTime", "")
        serving_size = row.get("ServingSize", "")
        ingredients = str(row["Ingredients"])
        directions = str(row["Directions"])
        photo_path = str(row.get("Photo", "")).strip()

        print(f"⚙️ Building recipe card for: {title}")

        # Determine if overflow is needed
        overflow = needs_overflow(ingredients, directions)

        # Context for Word template
        context = {
            "title": title,
            "servings": servings,
            "prep_time": prep_time,
            "cook_time": cook_time,
            "serving_size": serving_size,
            "ingredients": ingredients,
            "directions": directions,
            "ingredients_overflow": ingredients if overflow else "",
            "directions_overflow": directions if overflow else "",
            "notes_page1": "",
            "notes_page2": "",
            "notes_page3": "",
            "nutrition_macros": "Placeholder for Macros",
            "nutrition_micros": "Placeholder for Micros",
            "nutrition_additives": "Placeholder for Additives",
            "photo": photo_path,
            "overflow": "Yes" if overflow else "No",
        }

        # Load and render template
        doc = DocxTemplate(TEMPLATE_FILE)
        doc.render(context)

        # Save Word doc
        fname = f"{i+1:03d}-{slugify(title)}.docx"
        doc.save(OUTPUT_DIR / fname)

        # Add to Canva CSV
        canva_rows.append({
            "Title": title,
            "Servings": servings,
            "PrepTime": prep_time,
            "CookTime": cook_time,
            "ServingSize": serving_size,
            "Ingredients_P1": ingredients,
            "Directions_P1": directions,
            "Nutrition_Macros": "Placeholder for Macros",
            "Nutrition_Micros": "Placeholder for Micros",
            "Nutrition_Additives": "Placeholder for Additives",
            "Image": photo_path,
            "Overflow": "Yes" if overflow else "No"
        })

    # Export Canva CSV
    pd.DataFrame(canva_rows).to_csv(OUTPUT_CANVA, index=False)


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    print("🚀 Recipe builder started...")
    df = pd.read_csv(INPUT_CSV)
    build_outputs(df)
    print("✅ Finished building all recipe cards and Canva CSV.")
