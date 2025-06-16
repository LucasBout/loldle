import io
import discord
from PIL import ImageFont, Image, ImageDraw
from discord.ext import commands
from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()
token = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USERNAME"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE"),
}

@bot.command()
async def hello(ctx):
    await ctx.send("Bonjour ! Tapez /guess pour jouer au jeu.")

def get_champion_to_find():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT name, resource, position, gender, rangeType, released, region, genre, damageType FROM champions ORDER BY RAND() LIMIT 1")
        result = cursor.fetchone()
        return result
    except mysql.connector.Error as err:
        print(f"Erreur de connexion à la base de données : {err}")
        return None, None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_champions_by_name(name):
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT name, resource, position, gender, rangeType, released, region, genre, damageType FROM champions WHERE name LIKE %s", (f"%{name}%",))
        results = cursor.fetchall()
        return results[0] if results else None
    except mysql.connector.Error as err:
        print(f"Erreur de connexion à la base de données : {err}")
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_all_champions():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM champions order by name")
        results = cursor.fetchall()
        return results
    except mysql.connector.Error as err:
        print(f"Erreur de connexion à la base de données : {err}")
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def render_table_as_image(headers, row, guessed_champions, selected_champion, font_path="fonts/seguiemj.ttf", scale=2):
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"La police spécifiée n'a pas été trouvée : {font_path}")
    font_size = 40 * scale
    padding = 30 * scale
    spacing = 12 * scale
    border_width = 3 * scale
    header_bg = (44, 62, 80)  # Bleu foncé
    header_fg = (255, 255, 255)
    guessed_bg = (236, 240, 241)  # Gris clair
    answer_bg = (39, 174, 96)  # Vert
    answer_fg = (255, 255, 255)
    border_color = (52, 73, 94)
    font = ImageFont.truetype(font_path, font_size)

    # Calculer la largeur de chaque colonne
    col_widths = []
    for i in range(len(headers)):
        max_len = font.getlength(str(headers[i]))
        max_len = max(max_len, font.getlength(str(row[i]).encode('utf-16', 'surrogatepass').decode('utf-16')))
        if guessed_champions:
            for guessed_name in guessed_champions:
                if guessed_name != "" and guessed_name != row[0]:
                    guessed_champion = get_champions_by_name(guessed_name)
                    if guessed_champion:
                        cell = get_cell_display(headers[i], guessed_champion.get(headers[i], ""), row[i])
                        max_len = max(max_len,
                                      font.getlength(str(cell).encode('utf-16', 'surrogatepass').decode('utf-16')))
        col_widths.append(int(max_len + spacing * 2))

    table_width = int(sum(col_widths) + padding * 2 + border_width * (len(headers) + 1))

    # Calculer le nombre de lignes à afficher
    n_rows = 1  # headers
    guessed_rows = []
    if guessed_champions:
        for guessed_name in guessed_champions:
            if guessed_name != "" and guessed_name != row[0]:
                n_rows += 1
                guessed_rows.append(guessed_name)
    n_rows += 1  # ligne de la réponse

    table_height = int(n_rows * (font_size + spacing) + padding * 2 + border_width * (n_rows + 1))

    image = Image.new("RGB", (table_width, table_height), color="white")
    draw = ImageDraw.Draw(image)

    def draw_cell(x, y, w, h, text, font, fill, bg, border):
        # Coins arrondis pour un style moderne
        radius = int(min(w, h) * 0.18)
        rect = [x, y, x + w, y + h]
        draw.rounded_rectangle(rect, radius=radius, fill=bg, outline=border, width=border_width)
        text_w = font.getlength(str(text))
        text_h = font_size
        text_x = x + (w - text_w) / 2
        text_y = y + (h - text_h) / 2
        draw.text((text_x, text_y), str(text), font=font, fill=fill, encoding="utf-8")

    x0 = padding
    y0 = padding
    row_height = font_size + spacing

    # Header
    x = x0
    y = y0
    for i, header in enumerate(headers):
        draw_cell(x, y, col_widths[i], row_height, header, font, header_fg, header_bg, border_color)
        x += col_widths[i] + border_width

    # Lignes des champions devinés
    y += row_height + border_width
    if guessed_rows:
        for guessed_name in guessed_rows:
            x = x0
            guessed_champion = get_champions_by_name(guessed_name)
            if guessed_champion:
                guessed_values = [
                    get_cell_display(
                        headers[i],
                        guessed_champion.get(headers[i], ""),
                        row[i]
                    ) for i in range(len(headers))
                ]
                for i, cell in enumerate(guessed_values):
                    cell_display = get_cell_display(
                        headers[i], guessed_champion.get(headers[i], ""), selected_champion[headers[i]]
                    )
                    # Couleur selon l'icône
                    if headers[i] == "name":
                        color = "black"
                        cell_display = str(cell_display).split(" ")[0]
                    elif "✅" in cell_display:
                        color = "green"
                    elif "🟧" in cell_display:
                        color = "orange"
                    elif any(icon in cell_display for icon in ["❌", "⬇️", "⬆️"]):
                        color = "red"
                    else:
                        color = "black"
                    draw_cell(x, y, col_widths[i], row_height, cell_display, font, color, guessed_bg, border_color)
                    x += col_widths[i] + border_width
            y += row_height + border_width

    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output

def get_cell_display(key, guess_value, target_value, col_width=None):
    check_icon = "✅" if guess_value == target_value else "❌"
    if key == "gender":
        if guess_value == 1:
            label = "Male"
        elif guess_value == 2:
            label = "Female"
        else:
            label = str(guess_value)
        match = guess_value == target_value
        check_icon = "✅" if match else "❌"
        value = f"{label} {check_icon}"
    elif key in ["position", "genre", "region"]:
        def to_set(val):
            if isinstance(val, str):
                return set([v.strip() for v in val.split(",") if v.strip()])
            try:
                return set(val)
            except TypeError:
                return {val}

        guess_set = to_set(guess_value)
        target_set = to_set(target_value)
        if guess_set == target_set:
            match = True
            partial = False
        elif not guess_set.isdisjoint(target_set):
            match = False
            partial = True
        else:
            match = False
            partial = False
        label = ", ".join(guess_set)
        if match:
            check_icon = "✅"
        elif partial:
            check_icon = "🟧"
        else:
            check_icon = "❌"
        value = f"{label} {check_icon}"
    elif key == "released":
        if guess_value < target_value:
            arrow = "⬆️"
        elif guess_value > target_value:
            arrow = "⬇️"
        else:
            arrow = "✅"
        value = f"{guess_value} {arrow}"
    else:
        value = f"{guess_value} {check_icon}"
    if col_width is not None:
        return value.ljust(col_width)
    return value

class ChampionGuessView(discord.ui.View):
    def __init__(self, champion_list, selected_champion, page=0, guessed=None):
        super().__init__(timeout=None)
        self.champion_list = champion_list
        self.selected_champion = selected_champion
        self.page = page
        self.max_page = (len(champion_list) - 1) // 25
        self.guessed = guessed or []
        self.update_dropdown()

    def update_dropdown(self):
        self.clear_items()
        start = self.page * 25
        end = start + 25
        current_chunk = [
            champion for champion in self.champion_list[start:end]
            if champion not in self.guessed
        ]
        self.add_item(ChampionDropdown(current_chunk, self.selected_champion, self.guessed))

        if self.page > 0:
            self.add_item(PreviousPageButton(self))
        if self.page < self.max_page:
            self.add_item(NextPageButton(self))


class ChampionDropdown(discord.ui.Select):
    def __init__(self, options_chunk, selected_champion, guessed):
        self.selected_champion = selected_champion
        self.guessed = guessed
        options = [discord.SelectOption(label=name) for name in options_chunk]
        super().__init__(placeholder="Choisis un champion", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            await interaction.followup.send("L'interaction a expiré. Veuillez réessayer.", ephemeral=True)
            return

        user_guess = self.values[0]
        self.guessed.append(user_guess)

        if user_guess.lower() == self.selected_champion['name'].lower():
            await interaction.response.send_message(
                f"🎉 Bravo ! Tu as deviné le bon champion : **{user_guess}**", ephemeral=False
            )
            self.view.stop()
        else:
            await interaction.response.defer()  # Prolonge l'interaction
            champion_guess = get_champions_by_name(user_guess)

            headers_text = list(self.selected_champion.keys())
            values_text = [
                get_cell_display(
                    key,
                    champion_guess.get(key, ""),
                    self.selected_champion[key]
                ) for key in headers_text
            ]

            image_buffer = render_table_as_image(headers_text, values_text, self.guessed, self.selected_champion)
            file = discord.File(fp=image_buffer, filename="result.png")

            new_view = ChampionGuessView(
                champion_list=self.view.champion_list,
                selected_champion=self.selected_champion,
                page=self.view.page,
                guessed=self.guessed,
            )

            await interaction.followup.send(
                content=f"❌ Mauvais champion, réessaie !\n",
                file=file,
                view=new_view,
                ephemeral=False
            )


class NextPageButton(discord.ui.Button):
    def __init__(self, view: ChampionGuessView):
        super().__init__(label="Suivant", style=discord.ButtonStyle.primary, row=1)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page += 1
        self.view_ref.update_dropdown()
        await interaction.response.edit_message(view=self.view_ref)


class PreviousPageButton(discord.ui.Button):
    def __init__(self, view: ChampionGuessView):
        super().__init__(label="Précédent", style=discord.ButtonStyle.secondary, row=1)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page -= 1
        self.view_ref.update_dropdown()
        await interaction.response.edit_message(view=self.view_ref)


@bot.command()
async def guess(ctx):
    selected_champion = get_champion_to_find()
    if not selected_champion:
        await ctx.send("Impossible de récupérer les données du champion.")
        return

    champion_list = [champion['name'] for champion in get_all_champions()]
    view = ChampionGuessView(champion_list, selected_champion)
    await ctx.send("Devine le champion :", view=view)


bot.run(token)