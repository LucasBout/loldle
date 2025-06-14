import discord
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
        cursor.execute("SELECT * FROM champions")
        results = cursor.fetchall()
        return results
    except mysql.connector.Error as err:
        print(f"Erreur de connexion à la base de données : {err}")
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@bot.command()
async def guess(ctx):
    selected_champion = get_champion_to_find()
    if not selected_champion:
        await ctx.send("Impossible de récupérer les données du champion.")
        return

    await ctx.send("Devinez le champion :")

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    while True:
        try:
            user_message = await bot.wait_for("message", check=check)
            user_guess = user_message.content
            if user_guess.lower() == selected_champion['name'].lower():
                await ctx.send("Bravo ! Vous avez deviné correctement.")
                break
            else:
                champion_guess = get_champions_by_name(user_guess)
                await ctx.send(f"Incorrect ! Essayez encore. Points communs : {', '.join([champion_guess[key] for key in selected_champion if key in champion_guess and selected_champion[key] == champion_guess[key]])}")
        except Exception as e:
            await ctx.send("Une erreur s'est produite. Essayez à nouveau.")

bot.run(token)