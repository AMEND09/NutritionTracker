import json
import os
import datetime
import time
import requests
import subprocess
import sys
import statistics
from collections import Counter

import plotext as plt
from rich.console import Console
from rich.prompt import Prompt, FloatPrompt, IntPrompt
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.progress_bar import ProgressBar
from rich.text import Text

DATA_FILE = "tracker_data.json"
OPENFOODFACTS_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OPENFOODFACTS_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{}.json"
CONSOLE = Console()
MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snacks"]
MEAL_COLORS = {"Breakfast": "yellow", "Lunch": "green", "Dinner": "blue", "Snacks": "magenta"}
EXERCISE_DB = {
    "Running (10 min/mile)": 10.0, "Cycling (moderate)": 8.0, "Weightlifting (vigorous)": 6.0,
    "Walking (brisk)": 4.3, "Swimming (freestyle)": 7.0, "Yoga": 2.5,
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def format_nutrient(value):
    return f"{value or 0:.1f}"

class NutrientTracker:
    def __init__(self):
        self.data = self.load_or_setup_data()
        self.current_date_obj = datetime.date.today()
        self.current_date_iso = self.current_date_obj.isoformat()
        self.update_streaks()

    def load_or_setup_data(self):
        if not os.path.exists(DATA_FILE):
            CONSOLE.print("[bold yellow]Welcome to the Nutrient & Workout Tracker![/bold yellow]")
            CONSOLE.print("Let's get your profile set up.")
            profile, micro_goals = self.setup_user_profile()
            new_data = {
                "profile": profile, "micronutrient_goals": micro_goals,
                "custom_foods": [], "daily_logs": {}, "weight_logs": {},
                "search_history": [], "fasting": {'active': False, 'start_time': None, 'duration_hours': 16},
                "streaks": {'calorie_goal': 0, 'water_goal': 0, 'last_checked_date': None},
                "meal_plans": {}, "progress_photos": {}
            }
            save_data(new_data)
            return new_data
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            CONSOLE.print("[bold red]Data file is corrupted or unreadable. Starting fresh setup.[/bold red]")
            profile, micro_goals = self.setup_user_profile()
            new_data = {"profile": profile, "micronutrient_goals": micro_goals}
            save_data(new_data)
            data = new_data

        data.setdefault('weight_logs', {})
        data.setdefault('custom_foods', [])
        data.setdefault('daily_logs', {})
        data.setdefault('search_history', [])
        data.setdefault('fasting', {'active': False, 'start_time': None, 'duration_hours': 16})
        data.setdefault('streaks', {'calorie_goal': 0, 'water_goal': 0, 'last_checked_date': None})
        data.setdefault('meal_plans', {})
        data.setdefault('progress_photos', {})
        data.setdefault('micronutrient_goals', {'sodium_mg': 2300, 'sugar_g': 30})
        data.setdefault('profile', {}).setdefault('goals', {})
        return data

    def setup_user_profile(self, existing_data=None):

        if existing_data is None: existing_data = {}
        existing_profile = existing_data.get('profile', {})
        existing_micro_goals = existing_data.get('micronutrient_goals', {})

        profile = {}
        profile['name'] = Prompt.ask("What's your name?", default=existing_profile.get('name'))
        profile['age'] = IntPrompt.ask("What's your age?", default=existing_profile.get('age', 30))
        profile['sex'] = Prompt.ask("What's your sex?", choices=["male", "female"], default=existing_profile.get('sex', 'male'))
        current_weight = FloatPrompt.ask("Your current weight (kg)", default=existing_profile.get('weight_kg', 70.0))
        profile['weight_kg'] = current_weight
        profile['height_cm'] = FloatPrompt.ask("Your height (cm)", default=existing_profile.get('height_cm', 175.0))

        if 'start_weight_kg' in existing_profile:
            profile['start_weight_kg'] = existing_profile['start_weight_kg']
        else:
            profile['start_weight_kg'] = current_weight

        default_goal = round(current_weight * 0.95, 1)
        profile['goal_weight_kg'] = FloatPrompt.ask("Your goal weight (kg)", default=existing_profile.get('goal_weight_kg', default_goal))

        activity_levels = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
        activity_choice = Prompt.ask("What's your activity level?", choices=list(activity_levels.keys()), default=existing_profile.get('activity_level', 'moderate'))
        profile['activity_level'] = activity_choice

        if profile['sex'] == 'male':
            bmr = 88.362 + (13.397 * profile['weight_kg']) + (4.799 * profile['height_cm']) - (5.677 * profile['age'])
        else:
            bmr = 447.593 + (9.247 * profile['weight_kg']) + (3.098 * profile['height_cm']) - (4.330 * profile['age'])
        tdee = bmr * activity_levels[activity_choice]
        protein_g = profile['weight_kg'] * 1.8
        fat_calories = tdee * 0.25
        fat_g = fat_calories / 9
        carb_g = (tdee - (protein_g * 4) - fat_calories) / 4
        goals = { "calories": int(tdee), "protein_g": int(protein_g), "carbs_g": int(carb_g), "fats_g": int(fat_g) }

        if Prompt.ask("\nCustomize macro goals? [y/n]", default="n") == "y":
            goals['calories'] = IntPrompt.ask("Calories", default=goals['calories'])
            goals['protein_g'] = IntPrompt.ask("Protein (g)", default=goals['protein_g'])
            goals['carbs_g'] = IntPrompt.ask("Carbs (g)", default=goals['carbs_g'])
            goals['fats_g'] = IntPrompt.ask("Fats (g)", default=goals['fats_g'])

        goals['water_ml'] = IntPrompt.ask("Daily water goal (ml)", default=existing_profile.get('goals', {}).get('water_ml', 2500))
        profile['goals'] = goals

        micronutrient_goals = {}
        micronutrient_goals['sodium_mg'] = IntPrompt.ask("Daily sodium goal (mg)", default=existing_micro_goals.get('sodium_mg', 2300))
        micronutrient_goals['sugar_g'] = IntPrompt.ask("Daily added sugar goal (g)", default=existing_micro_goals.get('sugar_g', 30))

        CONSOLE.print("\n[bold green]Profile setup complete![/bold green]")
        time.sleep(2)
        return profile, micronutrient_goals

    def get_log_for_date(self, date_iso):
        if date_iso not in self.data["daily_logs"]:
            self.data["daily_logs"][date_iso] = {
                "meals": {meal: [] for meal in MEAL_TYPES},
                "workout_entries": [], "water_ml": 0, "notes": ""
            }
        log = self.data["daily_logs"][date_iso]
        log.setdefault("water_ml", 0)
        log.setdefault("meals", {meal: [] for meal in MEAL_TYPES})
        log.setdefault("workout_entries", [])
        for meal in MEAL_TYPES: log["meals"].setdefault(meal, [])
        return log

    def navigate_date(self, days_delta):
        self.current_date_obj += datetime.timedelta(days=days_delta)
        self.current_date_iso = self.current_date_obj.isoformat()

    def view_weight_history(self):
        clear_screen()
        logs = self.data.get('weight_logs', {})
        if len(logs) < 2:
            CONSOLE.print("[yellow]Not enough data for a graph. Log weight on at least two different days.[/yellow]")
            time.sleep(2.5); return

        sorted_logs = sorted(logs.items())
        dates = [item[0] for item in sorted_logs]
        weights = [item[1] for item in sorted_logs]

        plt.clear_figure()
        plt.plot_size(CONSOLE.width - 5, CONSOLE.height - 7)
        plt.date_form('Y-m-d'); plt.theme("dark"); plt.title("Weight Progression History")
        plt.plot(dates, weights, marker='o', color='cyan'); plt.show()
        Prompt.ask("\n[bold]Press Enter to return[/bold]")

    def build_dashboard_panel(self):
        layout = Layout(name="root")
        layout.split(
            Layout(name="header", size=3), Layout(ratio=1, name="main"), Layout(size=3, name="footer")
        )
        layout["main"].split_row(Layout(name="left", ratio=2), Layout(name="right", ratio=3))
        layout["left"].split_column(Layout(name="macros"), Layout(name="status_trackers"))
        layout["right"].split_column(Layout(name="food_log"), Layout(name="workout_log"))
        layout["status_trackers"].split_row(Layout(name="streaks"), Layout(name="fasting"))

        date_display_obj = self.current_date_obj
        if date_display_obj == datetime.date.today(): date_display = "Today"
        elif date_display_obj == datetime.date.today() - datetime.timedelta(days=1): date_display = "Yesterday"
        else: date_display = self.current_date_iso
        header_text = Text(f"Tracker for {self.data['profile']['name']} - {date_display}", justify="center", style="bold white on blue")
        layout["header"].update(Panel(header_text))

        log = self.get_log_for_date(self.current_date_iso)
        goals = self.data['profile']['goals']
        micro_goals = self.data['micronutrient_goals']
        all_food = [item for meal_entries in log['meals'].values() for item in meal_entries]

        totals = {
            "calories": sum(f.get('calories', 0) for f in all_food), "protein": sum(f.get('protein_g', 0) for f in all_food),
            "carbs": sum(f.get('carbs_g', 0) for f in all_food), "fats": sum(f.get('fats_g', 0) for f in all_food),
            "water": log.get('water_ml', 0), "sodium": sum(f.get('micros', {}).get('sodium_mg', 0) for f in all_food),
            "sugar": sum(f.get('micros', {}).get('sugar_g', 0) for f in all_food)
        }

        summary_table = Table(show_header=False, expand=True, title="[bold]Daily Summary[/bold]", title_justify="left", padding=0)
        summary_table.add_column("Metric"); summary_table.add_column("Value", justify="right"); summary_table.add_column("Progress")

        metrics = [
            ("Calories", totals['calories'], goals.get('calories', 2000), "kcal", "magenta"),
            ("Protein", totals['protein'], goals.get('protein_g', 100), "g", "green"),
            ("Carbs", totals['carbs'], goals.get('carbs_g', 200), "g", "yellow"),
            ("Fats", totals['fats'], goals.get('fats_g', 70), "g", "cyan"),
            ("Water", totals['water'], goals.get('water_ml', 2500), "ml", "bright_blue"),
            ("Sodium", totals['sodium'], micro_goals.get('sodium_mg', 2300), "mg", "red"),
            ("Sugar", totals['sugar'], micro_goals.get('sugar_g', 30), "g", "bright_magenta")
        ]

        for name, current, goal, unit, color in metrics:
            progress = min(current / goal, 1.0) if goal > 0 else 0
            bar = ProgressBar(total=1.0, completed=progress, width=15)
            summary_table.add_row(Text(name, style=color), f"{format_nutrient(current)} / {goal} {unit}", bar)
        

        layout["macros"].update(Panel(summary_table, title="[bold]Nutrition[/bold]", border_style="cyan"))

        streaks = self.data['streaks']
        streak_panel = Panel(
            f":fire: Calorie Goal: [bold green]{streaks.get('calorie_goal', 0)} days[/]\n"
            f":droplet: Water Goal: [bold blue]{streaks.get('water_goal', 0)} days[/]",
            title="[bold]Streaks[/bold]", border_style="yellow"
        )
        layout["streaks"].update(streak_panel)

        fasting_data = self.data['fasting']
        fasting_content = "[dim]No active fast.[/dim]\n[dim]Press 'f' to start one.[/dim]"
        if fasting_data['active'] and fasting_data['start_time']:
            start_ts = datetime.datetime.fromisoformat(fasting_data['start_time']).timestamp()
            now_ts = datetime.datetime.now().timestamp()
            duration_sec = fasting_data['duration_hours'] * 3600
            elapsed_sec = now_ts - start_ts
            progress = min(elapsed_sec / duration_sec, 1.0)
            elapsed_h, rem_m_div = divmod(elapsed_sec, 3600)
            elapsed_m = rem_m_div / 60
            remaining_sec = max(0, duration_sec - elapsed_sec)
            rem_h, rem_m_rem_div = divmod(remaining_sec, 3600)
            rem_m = rem_m_rem_div / 60
            bar = ProgressBar(total=1.0, completed=progress, width=20)
            fasting_content = (f"Status: [bold green]FASTING[/]\n"
                             f"Elapsed: {int(elapsed_h)}h {int(elapsed_m)}m\n"
                             f"Remaining: {int(rem_h)}h {int(rem_m)}m\n{bar}")
        layout["fasting"].update(Panel(fasting_content, title="[bold]Fasting[/bold]", border_style="magenta"))

        food_table = Table(expand=True, show_header=False, padding=(0, 1))
        food_table.add_column("Meal/Food", ratio=5); food_table.add_column("Cals", justify="right", ratio=1)
        food_table.add_column("P", justify="right", ratio=1); food_table.add_column("C", justify="right", ratio=1)
        food_table.add_column("F", justify="right", ratio=1)

        has_food = any(log['meals'].values())
        if self.current_date_obj > datetime.date.today() and self.current_date_iso in self.data['meal_plans']:
            plan = self.data['meal_plans'][self.current_date_iso]
            food_table.add_row("[bold]PLANNED MEALS[/bold]", style="cyan", end_section=True)
            for meal_name, items in plan.items():
                if items:
                    food_table.add_row(f"[bold dim]{meal_name}[/]", end_section=True)
                    for item in items: food_table.add_row(f"  - {item}")
        elif has_food:
            for meal_name, entries in log['meals'].items():
                if entries:
                    color = MEAL_COLORS.get(meal_name, "white")
                    food_table.add_row(f"[bold white on {color}] {meal_name} [/]", style=f"on {color}", end_section=True)
                    for entry in entries:
                        food_table.add_row(f"  {entry['name']}", format_nutrient(entry['calories']),
                                           format_nutrient(entry['protein_g']), format_nutrient(entry['carbs_g']),
                                           format_nutrient(entry['fats_g']))
        else:
            food_table.add_row(Text("No food logged for this day.", justify="center", style="dim"))
        layout["food_log"].update(Panel(food_table, title="[bold]Food Log[/bold]", border_style="green"))

        workout_table = Table(expand=True, title_justify="left")
        workout_table.add_column("Exercise", style="cyan"); workout_table.add_column("Mins", justify="right")
        workout_table.add_column("Cals Burned", justify="right")
        if log.get('workout_entries'):
            for entry in log['workout_entries']:
                workout_table.add_row(entry['name'], str(entry['duration_min']), format_nutrient(entry['calories_burned']))
        layout["workout_log"].update(Panel(workout_table, title="[bold]Workouts[/bold]", border_style="yellow"))

        footer_text = Text("[1] Log Food | [2] Log Workout | [3] Log Weight | [4] Log Water | [f] Fasting | [m] More... | [<] Prev | [>] Next | [q] Quit", justify="center")
        layout["footer"].update(Panel(footer_text, border_style="dim"))
        return Panel(layout)

    def log_food(self):
        clear_screen()
        CONSOLE.print(Panel(f"[bold]Log Food for {self.current_date_iso}[/bold]", expand=False, border_style="green"))
        meal_choice = Prompt.ask("Which meal?", choices=MEAL_TYPES, default="Snacks")

        methods = [
            ('s', 'Search API'),
            ('f', 'Frequent Foods'),
            ('c', 'Custom Food List'),
            ('b', 'Barcode'),
        ]
        if self.data['search_history']:
            methods.insert(1, ('h', 'Search History'))
        methods.append(('x', 'Cancel'))

        method_table = Table(title="How would you like to log?", show_header=False, title_style="bold green")
        method_table.add_column("#", style="cyan", justify="right")
        method_table.add_column("Method")
        for i, (_, desc) in enumerate(methods, 1):
            method_table.add_row(str(i), desc)
        CONSOLE.print(method_table)

        choice_num = IntPrompt.ask("Choose an option", choices=[str(i) for i in range(1, len(methods) + 1)], show_choices=False)
        method_key = methods[choice_num - 1][0]

        food_entry = None
        if method_key == 'f': food_entry = self.get_food_from_frequent()
        elif method_key == 'c': food_entry = self.get_food_from_custom()
        elif method_key == 'h': food_entry = self.get_food_from_history()
        elif method_key == 'b': food_entry = self.get_food_from_barcode()
        elif method_key == 's': food_entry = self.get_food_from_search()
        elif method_key == 'x':
            CONSOLE.print("[yellow]Cancelled.[/yellow]"); time.sleep(1); return

        if food_entry:
            self.get_log_for_date(self.current_date_iso)['meals'][meal_choice].append(food_entry)
            save_data(self.data)
            CONSOLE.print(f"[green]'{food_entry['name']}' logged to {meal_choice}.[/green]")
            time.sleep(1.5)

    def get_frequent_foods(self, limit=10):
        all_names = [food['name'] for day in self.data['daily_logs'].values() for meal in day['meals'].values() for food in meal]
        if not all_names: return []
        return [item[0] for item in Counter(all_names).most_common(limit)]

    def get_food_from_frequent(self):
        frequent_foods = self.get_frequent_foods()
        if not frequent_foods:
            CONSOLE.print("[yellow]No frequent foods logged yet. Searching instead...[/yellow]"); time.sleep(1.5); return self.get_food_from_search()

        table = Table(title="Your Frequent Foods")
        table.add_column("#", style="cyan", justify="right"); table.add_column("Food Name")
        for i, name in enumerate(frequent_foods, 1): table.add_row(str(i), name)
        CONSOLE.print(table)
        choice = IntPrompt.ask("Enter # to log (or 0 to search instead)", choices=[str(i) for i in range(len(frequent_foods) + 1)], default="1")
        if choice == 0: return self.get_food_from_search()
        food_name = frequent_foods[choice - 1]
        for day in reversed(list(self.data['daily_logs'].values())):
            for meal in day['meals'].values():
                for food in meal:
                    if food['name'] == food_name:
                        return self.scale_food_entry(food)
        return None

    def get_food_from_history(self):
        history = self.data['search_history']
        if not history: CONSOLE.print("[yellow]No search history.[/yellow]"); time.sleep(1); return None
        table = Table(title="Recent Searches")
        table.add_column("#", style="cyan", justify="right"); table.add_column("Search Term")
        for i, term in enumerate(history, 1): table.add_row(str(i), term)
        CONSOLE.print(table)
        choice = IntPrompt.ask("Enter # to search again (or 0 to cancel)", choices=[str(i) for i in range(len(history) + 1)], default="1")
        if choice == 0: return None
        return self.get_food_from_search(query=history[choice - 1])

    def get_food_from_search(self, query=None):
        if not query:
            query = Prompt.ask("Search for a food")
            if not query: return None
            if query in self.data['search_history']: self.data['search_history'].remove(query)
            self.data['search_history'].insert(0, query)
            self.data['search_history'] = self.data['search_history'][:10]
            save_data(self.data)
        return self.search_and_select_product({"search_terms": query, "search_simple": 1, "action": "process", "json": 1, "page_size": 10})

    def get_food_from_barcode(self):
        barcode = Prompt.ask("Enter barcode number")
        if not barcode: return None
        url = OPENFOODFACTS_PRODUCT_URL.format(barcode)
        try:
            with CONSOLE.status("[yellow]Searching Open Food Facts by barcode...[/yellow]"):
                response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != 1 or "product" not in data:
                 CONSOLE.print(f"[yellow]Product with barcode '{barcode}' not found.[/yellow]"); time.sleep(2); return None
            return self.process_product_selection(data['product'])
        except requests.exceptions.RequestException:
            CONSOLE.print("[bold red]API request failed.[/bold red]"); time.sleep(2); return None

    def search_and_select_product(self, params):
        try:
            with CONSOLE.status("[yellow]Searching Open Food Facts API...[/yellow]"):
                response = requests.get(OPENFOODFACTS_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            search_results = response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            CONSOLE.print("[bold red]API request failed.[/bold red]"); time.sleep(2); return None
        if not search_results.get("products"):
            CONSOLE.print("[yellow]No products found.[/yellow]"); time.sleep(2); return None
        valid_products = [p for p in search_results['products'] if p.get('product_name') and p.get('nutriments', {}).get('energy-kcal_100g') is not None]
        if not valid_products:
            CONSOLE.print("[yellow]Found products, but none had usable nutritional data.[/yellow]"); time.sleep(2); return None

        results_table = Table(title="Search Results")
        results_table.add_column("#", style="magenta"); results_table.add_column("Product Name"); results_table.add_column("Brand")
        for i, p in enumerate(valid_products, 1):
             results_table.add_row(str(i), p.get('product_name_en') or p.get('product_name', 'N/A'), p.get('brands', 'N/A'))
        CONSOLE.print(results_table)
        choice = IntPrompt.ask("Enter # to log (or 0 to cancel)", choices=[str(i) for i in range(len(valid_products) + 1)], default="0")
        if choice == 0: return None
        return self.process_product_selection(valid_products[choice - 1])

    def process_product_selection(self, product):
        product_name = product.get('product_name_en') or product.get('product_name', 'Unknown Food')
        nutriments = product['nutriments']
        grams_consumed = FloatPrompt.ask(f"How many grams of '{product_name}'?", default=100.0)
        scale = grams_consumed / 100.0
        def safe_float(value, default=0.0):
            try: return float(value)
            except (ValueError, TypeError): return default
        return {"name": product_name, "grams": grams_consumed,
                "calories":  safe_float(nutriments.get('energy-kcal_100g')) * scale,
                "protein_g": safe_float(nutriments.get('proteins_100g')) * scale,
                "carbs_g":   safe_float(nutriments.get('carbohydrates_100g')) * scale,
                "fats_g":    safe_float(nutriments.get('fat_100g')) * scale,
                "micros": {"sodium_mg": safe_float(nutriments.get('sodium_100g')) * 1000 * scale,
                           "sugar_g":   safe_float(nutriments.get('sugars_100g')) * scale,
                           "fiber_g":   safe_float(nutriments.get('fiber_100g')) * scale,}}

    def scale_food_entry(self, food_entry):
        grams = FloatPrompt.ask(f"How many grams of '{food_entry['name']}'?", default=food_entry.get('serving_size_g') or food_entry.get('grams') or 100.0)
        base_grams = food_entry.get('serving_size_g') or food_entry.get('grams') or 100.0
        if base_grams == 0: return None
        scale = grams / base_grams
        scaled_entry = food_entry.copy()
        scaled_entry['grams'] = grams
        for key in ['calories', 'protein_g', 'carbs_g', 'fats_g']:
            if key in scaled_entry: scaled_entry[key] = (scaled_entry.get(key) or 0) * scale
        if 'micros' in scaled_entry and scaled_entry.get('micros'):
            for micro_key in scaled_entry['micros']:
                scaled_entry['micros'][micro_key] = (scaled_entry['micros'].get(micro_key) or 0) * scale
        return scaled_entry

    def get_food_from_custom(self):
        custom_foods = self.data.get('custom_foods', [])
        if not custom_foods:
            CONSOLE.print("[yellow]No custom foods/recipes. Add one from the 'More...' menu.[/yellow]"); time.sleep(2); return None
        table = Table(title="Your Custom Foods & Recipes")
        table.add_column("#", style="magenta"); table.add_column("Name"); table.add_column("Serving Size (g)")
        for i, food in enumerate(custom_foods, 1): table.add_row(str(i), food['name'], str(food['serving_size_g']))
        CONSOLE.print(table)
        choice = IntPrompt.ask("Enter # to log (or 0 to cancel)", choices=[str(i) for i in range(len(custom_foods) + 1)], default="0")
        if choice == 0: return None
        return self.scale_food_entry(custom_foods[choice-1])

    def log_workout(self):
        clear_screen()
        CONSOLE.print(Panel("[bold]Log Workout[/bold]", expand=False, border_style="yellow"))
        log_type = Prompt.ask("Log from", choices=["database", "manual"], default="database")
        name = ""; duration = 0; calories = 0
        if log_type == "database":
            table = Table(title="Exercise Database")
            db_list = list(EXERCISE_DB.keys())
            table.add_column("#"); table.add_column("Exercise")
            for i, ex in enumerate(db_list, 1): table.add_row(str(i), ex)
            CONSOLE.print(table)
            choice = IntPrompt.ask("Choose exercise # (or 0 for manual entry)", choices=[str(i) for i in range(len(db_list) + 1)], default="1")
            if choice == 0: log_type = "manual"
            else:
                name = db_list[choice-1]
                duration = IntPrompt.ask(f"Duration for '{name}' (minutes)")
                met_value = EXERCISE_DB[name]
                calories = met_value * self.data['profile']['weight_kg'] * (duration / 60)
                CONSOLE.print(f"Estimated calories burned: [bold yellow]{calories:.0f}[/]")
        if log_type == "manual":
            name = Prompt.ask("Exercise name")
            if not name: return
            duration = IntPrompt.ask("Duration (minutes)")
            calories = FloatPrompt.ask("Estimated calories burned")
        self.get_log_for_date(self.current_date_iso)['workout_entries'].append({"name": name, "duration_min": duration, "calories_burned": calories})
        save_data(self.data)
        CONSOLE.print("[green]Workout logged.[/green]"); time.sleep(1)

    def log_water(self):
        clear_screen()
        CONSOLE.print(Panel("[bold]Log Water Intake[/bold]", expand=False, border_style="bright_blue"))
        current_log = self.get_log_for_date(self.current_date_iso)
        CONSOLE.print(f"Current intake for today: [cyan]{current_log.get('water_ml', 0)} ml[/cyan]")
        amount = IntPrompt.ask("How much water to add (ml)?", default=250)
        if amount > 0:
            current_log['water_ml'] += amount
            save_data(self.data)
            CONSOLE.print(f"[green]Added {amount} ml. New total: {current_log['water_ml']} ml.[/green]")
        else:
            CONSOLE.print("[yellow]No water added.[/yellow]")
        time.sleep(1.5)

    def log_weight(self):
        clear_screen()
        CONSOLE.print(Panel("[bold]Log Weight[/bold]", expand=False, border_style="blue"))
        new_weight = FloatPrompt.ask("Enter current weight (kg)", default=self.data['profile']['weight_kg'])
        self.data['weight_logs'][self.current_date_iso] = new_weight
        self.data['profile']['weight_kg'] = new_weight
        save_data(self.data)

    def manage_custom_food_recipes(self):
        clear_screen()
        CONSOLE.print(Panel("[bold]Add Custom Food or Recipe[/bold]", expand=False, border_style="cyan"))
        add_type = Prompt.ask("Add a single food or a multi-ingredient recipe?", choices=["food", "recipe"], default="food")
        if add_type == "food":
            name = Prompt.ask("Food Name")
            if not name: return
            serving = FloatPrompt.ask("Serving size (grams)", default=100.0)
            calories = FloatPrompt.ask("Calories per serving")
            protein = FloatPrompt.ask("Protein (g) per serving")
            carbs = FloatPrompt.ask("Carbs (g) per serving")
            fats = FloatPrompt.ask("Fats (g) per serving")
            self.data.setdefault('custom_foods', []).append({"name": name, "serving_size_g": serving, "calories": calories, "protein_g": protein, "carbs_g": carbs, "fats_g": fats, "micros": {}})
        else: 
            recipe_name = Prompt.ask("Recipe Name")
            if not recipe_name: return
            ingredients = []
            while True:
                ingredient_entry = self.get_food_from_search()
                if ingredient_entry:
                    ingredients.append(ingredient_entry)
                    CONSOLE.print(f"[green]Added '{ingredient_entry['name']}' to recipe.[/green]")
                    if Prompt.ask("Add another ingredient? [y/n]", default='y') == 'n': break
                else:
                    if Prompt.ask("Failed to add. Try again? [y/n]", default='n') == 'n': break

            if not ingredients: CONSOLE.print("[yellow]Recipe cancelled.[/yellow]"); return
            total_recipe = {"name": recipe_name, "serving_size_g": 0, "calories": 0, "protein_g": 0, "carbs_g": 0, "fats_g": 0, "micros": {"sodium_mg": 0, "sugar_g": 0}}
            for ing in ingredients:
                total_recipe['serving_size_g'] += ing['grams']
                total_recipe['calories'] += ing['calories']
                total_recipe['protein_g'] += ing['protein_g']
                total_recipe['carbs_g'] += ing['carbs_g']
                total_recipe['fats_g'] += ing['fats_g']
                if 'micros' in ing and ing['micros']:
                    total_recipe['micros']['sodium_mg'] += ing['micros'].get('sodium_mg', 0)
                    total_recipe['micros']['sugar_g'] += ing['micros'].get('sugar_g', 0)
            self.data.setdefault('custom_foods', []).append(total_recipe)
        save_data(self.data)
        CONSOLE.print("[green]Saved successfully![/green]"); time.sleep(1)

    def manage_fasting(self):
        clear_screen()
        fasting_data = self.data['fasting']
        if fasting_data['active']:
            if Prompt.ask("A fast is currently active. End it? [y/n]", default="y") == 'y':
                fasting_data['active'] = False
                CONSOLE.print("[green]Fast ended. You are now in your eating window.[/green]")
            else: return
        else:
            CONSOLE.print("Starting a new fast.")
            duration = IntPrompt.ask("Enter fast duration in hours (e.g., 16, 18, 20)", default=fasting_data.get('duration_hours', 16))
            fasting_data['active'] = True
            fasting_data['start_time'] = datetime.datetime.now().isoformat()
            fasting_data['duration_hours'] = duration
            CONSOLE.print(f"[green]Fast started for {duration} hours.[/green]")
        save_data(self.data)
        time.sleep(2)

    def update_streaks(self):
        streaks = self.data['streaks']
        today_iso = datetime.date.today().isoformat()
        if streaks.get('last_checked_date') == today_iso: return
        yesterday_obj = datetime.date.today() - datetime.timedelta(days=1)
        yesterday_iso = yesterday_obj.isoformat()
        if streaks.get('last_checked_date') != yesterday_iso:
            streaks['calorie_goal'] = 0; streaks['water_goal'] = 0
        yesterday_log = self.data['daily_logs'].get(yesterday_iso)
        if yesterday_log:
            goals = self.data['profile']['goals']
            all_food = [item for meal in yesterday_log['meals'].values() for item in meal]
            total_calories = sum(f.get('calories', 0) for f in all_food)
            if total_calories > 0 and abs(total_calories - goals.get('calories', 0)) <= 100:
                streaks['calorie_goal'] = streaks.get('calorie_goal', 0) + 1
            else: streaks['calorie_goal'] = 0
            if yesterday_log.get('water_ml', 0) >= goals.get('water_ml', 2500):
                streaks['water_goal'] = streaks.get('water_goal', 0) + 1
            else: streaks['water_goal'] = 0
        streaks['last_checked_date'] = today_iso
        self.data['streaks'] = streaks

    def view_summary_reports(self):
        clear_screen()
        period = Prompt.ask("View report for", choices=["weekly", "monthly"], default="weekly")
        num_days = 7 if period == "weekly" else 30
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=num_days - 1)
        relevant_logs = {d: self.data['daily_logs'][d] for d in self.data['daily_logs'] if start_date <= datetime.date.fromisoformat(d) <= end_date}
        if not relevant_logs:
            CONSOLE.print(f"[yellow]No data found for the last {num_days} days.[/yellow]"); time.sleep(2); return
        daily_cals, daily_prot, daily_carbs, daily_fats, daily_water, dates = [], [], [], [], [], []
        for date_str in [(start_date + datetime.timedelta(days=i)).isoformat() for i in range(num_days)]:
            log = relevant_logs.get(date_str)
            dates.append(date_str)
            if log:
                all_food = [item for meal in log['meals'].values() for item in meal]
                daily_cals.append(sum(f.get('calories', 0) for f in all_food))
                daily_prot.append(sum(f.get('protein_g', 0) for f in all_food))
                daily_carbs.append(sum(f.get('carbs_g', 0) for f in all_food))
                daily_fats.append(sum(f.get('fats_g', 0) for f in all_food))
                daily_water.append(log.get('water_ml', 0))
            else:
                daily_cals.append(0); daily_prot.append(0); daily_carbs.append(0); daily_fats.append(0); daily_water.append(0)
        avg_table = Table(title=f"[bold]{period.title()} Averages ({len(relevant_logs)} logged days)[/bold]")
        avg_table.add_column("Metric", style="cyan"); avg_table.add_column("Average", justify="right"); avg_table.add_column("Goal", justify="right")
        goals = self.data['profile']['goals']
        avg_table.add_row("Calories", f"{statistics.mean(daily_cals):.0f} kcal", f"{goals.get('calories', 0)} kcal")
        avg_table.add_row("Protein", f"{statistics.mean(daily_prot):.1f} g", f"{goals.get('protein_g', 0)} g")
        avg_table.add_row("Carbs", f"{statistics.mean(daily_carbs):.1f} g", f"{goals.get('carbs_g', 0)} g")
        avg_table.add_row("Fats", f"{statistics.mean(daily_fats):.1f} g", f"{goals.get('fats_g', 0)} g")
        avg_table.add_row("Water", f"{statistics.mean(daily_water):.0f} ml", f"{goals.get('water_ml', 0)} ml")
        CONSOLE.print(avg_table)

        relevant_weights = {d: w for d, w in self.data['weight_logs'].items() if start_date <= datetime.date.fromisoformat(d) <= end_date}
        if len(relevant_weights) >= 2 and period == 'weekly':
            sorted_weights = sorted(relevant_weights.items())
            weight_change = sorted_weights[-1][1] - sorted_weights[0][1]
            avg_calories = statistics.mean(c for c in daily_cals if c > 0) if any(c > 0 for c in daily_cals) else 0
            advice = ""
            if self.data['profile']['goal_weight_kg'] < self.data['profile']['weight_kg']: 
                if weight_change > -0.2: advice = f"Weight loss is slow. Consider reducing calories from ~{avg_calories:.0f} to ~{avg_calories-200:.0f}."
                elif weight_change < -1.0: advice = f"Losing weight quickly. If you feel low-energy, consider increasing calories to ~{avg_calories+150:.0f}."
            else: 
                if weight_change < 0.2: advice = f"Weight gain is slow. Consider increasing calories from ~{avg_calories:.0f} to ~{avg_calories+250:.0f}."
            if advice: CONSOLE.print(Panel(f"[bold yellow]Trend Advice:[/] {advice}", border_style="yellow"))

        if Prompt.ask("\nShow trend graph? [y/n]", default="y") == 'y':
            plt.clear_figure(); plt.plot_size(CONSOLE.width - 5, CONSOLE.height - 7)
            plt.date_form('Y-m-d'); plt.theme("dark"); plt.title(f"{period.title()} Calorie & Macro Trends")
            plt.plot(dates, daily_cals, label="Calories", color="magenta")
            plt.plot(dates, [p * 4 for p in daily_prot], label="Protein cals", color="green")
            plt.plot(dates, [c * 4 for c in daily_carbs], label="Carb cals", color="yellow")
            plt.plot(dates, [f * 9 for f in daily_fats], label="Fat cals", color="cyan")
            plt.show()
        Prompt.ask("\n[bold]Press Enter to return[/bold]")

    def manage_meal_plan(self):
        clear_screen()
        CONSOLE.print(Panel("[bold]Meal Planner[/bold]", border_style="cyan"))
        offset = IntPrompt.ask("Plan for how many days from now? (e.g., 1 for tomorrow)", default=1)
        plan_date_obj = datetime.date.today() + datetime.timedelta(days=offset)
        plan_date_iso = plan_date_obj.isoformat()
        self.data['meal_plans'].setdefault(plan_date_iso, {m: [] for m in MEAL_TYPES})
        plan = self.data['meal_plans'][plan_date_iso]
        while True:
            clear_screen()
            CONSOLE.print(f"[bold]Editing Plan for {plan_date_iso}[/bold]")
            plan_table = Table(show_header=False)
            plan_table.add_column("Meal"); plan_table.add_column("Items")
            for meal, items in plan.items():
                plan_table.add_row(f"[bold {MEAL_COLORS[meal]}]{meal}[/]", "\n".join(f"- {i}" for i in items))
            CONSOLE.print(plan_table)
            action = Prompt.ask("\n[A]dd item, [R]emove item, or [D]one?", choices=['a', 'r', 'd'], default='d')
            if action == 'd': break
            elif action == 'a':
                meal_to_add = Prompt.ask("Add to which meal?", choices=MEAL_TYPES)
                item_name = Prompt.ask("Enter food/item name")
                if item_name: plan[meal_to_add].append(item_name)
            elif action == 'r':
                meal_to_remove = Prompt.ask("Remove from which meal?", choices=MEAL_TYPES)
                if plan[meal_to_remove]:
                    item_to_remove = Prompt.ask("Enter exact name to remove", choices=plan[meal_to_remove])
                    if item_to_remove in plan[meal_to_remove]: plan[meal_to_remove].remove(item_to_remove)
        save_data(self.data)

    def manage_progress_photos(self):
        clear_screen()
        action = Prompt.ask("What do you want to do?", choices=["log", "compare", "cancel"], default="log")
        photos = self.data.get('progress_photos', {})
        if action == "log":
            path = Prompt.ask("Enter the full path to your photo")
            if os.path.exists(path):
                photos[self.current_date_iso] = path
                CONSOLE.print("[green]Photo path logged for today.[/green]"); save_data(self.data)
            else: CONSOLE.print("[red]File path not found. Please enter a valid path.[/red]")
        elif action == "compare":
            if len(photos) < 2:
                CONSOLE.print("[yellow]You need to log at least two photos to compare.[/yellow]"); time.sleep(2); return
            sorted_photos = sorted(photos.items())
            table = Table(title="Logged Photos")
            table.add_column("#"); table.add_column("Date"); table.add_column("Path")
            for i, (date, path) in enumerate(sorted_photos, 1): table.add_row(str(i), date, path)
            CONSOLE.print(table)
            choice1 = IntPrompt.ask("Choose first photo #", choices=[str(i) for i in range(1, len(sorted_photos) + 1)])
            choice2 = IntPrompt.ask("Choose second photo #", choices=[str(i) for i in range(1, len(sorted_photos) + 1)])
            path1, path2 = sorted_photos[choice1-1][1], sorted_photos[choice2-1][1]
            try:
                CONSOLE.print(f"Attempting to open {path1} and {path2} with the default system viewer...")
                if sys.platform == "win32": os.startfile(path1); os.startfile(path2)
                elif sys.platform == "darwin": subprocess.call(["open", path1]); subprocess.call(["open", path2])
                else: subprocess.call(["xdg-open", path1]); subprocess.call(["xdg-open", path2])
            except Exception as e: CONSOLE.print(f"[bold red]Could not open photos: {e}[/bold red]")
        time.sleep(2)

    def export_data(self):
        backup_filename = f"tracker_data_backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        try:
            with open(DATA_FILE, 'r') as f_in, open(backup_filename, 'w') as f_out:
                f_out.write(f_in.read())
            CONSOLE.print(f"[green]Data successfully backed up to '{backup_filename}'[/green]")
        except Exception as e: CONSOLE.print(f"[red]Failed to create backup: {e}[/red]")
        time.sleep(2)

    def edit_profile(self):
        clear_screen()
        CONSOLE.print("[bold yellow]This will guide you through the setup process again to update your profile and goals.[/bold yellow]")
        if Prompt.ask("Continue? [y/n]", default="y") == "y":
            new_profile, new_micro_goals = self.setup_user_profile(existing_data=self.data)
            self.data['profile'] = new_profile
            self.data['micronutrient_goals'] = new_micro_goals
            save_data(self.data)
            CONSOLE.print("[green]Profile updated.[/green]")
        time.sleep(1.5)

    def show_more_menu(self):
        clear_screen()
        choice_map = {
            '1': ("Weekly/Monthly Summary", self.view_summary_reports),
            '2': ("Weight History Graph", self.view_weight_history),
            '3': ("Meal Planner", self.manage_meal_plan),
            '4': ("Add Custom Food/Recipe", self.manage_custom_food_recipes),
            '5': ("Manage Progress Photos", self.manage_progress_photos),
            '6': ("Export/Backup Data", self.export_data),
            '7': ("Edit Profile", self.edit_profile),
            'b': ("Back to Dashboard", None)
        }
        menu_text = "[bold cyan]More Options[/bold cyan]\n" + "\n".join([f"  [{k}] {v[0]}" for k, v in choice_map.items()])
        CONSOLE.print(Panel(menu_text))
        action = Prompt.ask("Choose an option", choices=list(choice_map.keys()), default='b')
        if action != 'b': choice_map[action][1]()

    def run(self):
        while True:
            clear_screen()
            CONSOLE.print(self.build_dashboard_panel())

            try:
                action = Prompt.ask(
                    "Action",
                    choices=['1', '2', '3', '4', 'f', 'm', '<', '>', 'q'],
                    show_choices=False, default='q'
                )

                if action == '1': self.log_food()
                elif action == '2': self.log_workout()
                elif action == '3': self.log_weight()
                elif action == '4': self.log_water()
                elif action.lower() == 'f': self.manage_fasting()
                elif action.lower() == 'm': self.show_more_menu()
                elif action == '<': self.navigate_date(-1)
                elif action == '>': self.navigate_date(1)
                elif action.lower() == 'q': break

            except Exception as e:
                clear_screen()
                CONSOLE.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
                CONSOLE.print_exception(show_locals=True)
                CONSOLE.print("\nThe application state has been saved. Please restart the application.")
                save_data(self.data) 
                time.sleep(10)
                break

if __name__ == "__main__":
    app = NutrientTracker()
    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        clear_screen()
        CONSOLE.print("[bold blue]Goodbye![/bold blue]")