import os
import discord
from discord.ext import commands
import sqlite3
from datetime import date

# ===============================
# CONFIGURACIÓN
# ===============================
FORM_CHANNEL_ID = 1465764092978532547     # Canal del formulario
LOG_CHANNEL_ID = 1462316362515873947      # Canal donde llegan los registros
RANKING_CHANNEL_ID = 1462316362515873948  # Canal del ranking
TOKEN = os.getenv("DISCORD_TOKEN")

# ===============================
# CONFIGURACIÓN DEL BOT
# ===============================
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

# ===============================
# BASE DE DATOS
# ===============================
db = sqlite3.connect("shulker.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS shulker (
    user_id INTEGER,
    username TEXT,
    fecha TEXT,
    total INTEGER
)
""")
db.commit()

# ===============================
# FUNCIÓN RANKING
# ===============================
async def actualizar_ranking(bot):
    hoy = str(date.today())

    cursor.execute("""
        SELECT username, total
        FROM shulker
        WHERE fecha = ?
        ORDER BY total DESC
    """, (hoy,))
    datos = cursor.fetchall()

    if not datos:
        return

    descripcion = ""
    for i, (user, total) in enumerate(datos, start=1):
        descripcion += f"**{i}. {user}** — {total} shulker\n"

    embed = discord.Embed(
        title="🏆 Ranking Diario de Shulker",
        description=descripcion,
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Fecha: {hoy}")

    channel = bot.get_channel(RANKING_CHANNEL_ID)
    if not channel:
        return

    async for msg in channel.history(limit=10):
        if msg.author == bot.user and msg.embeds:
            await msg.edit(embed=embed)
            return

    await channel.send(embed=embed)

# ===============================
# MODAL (FORMULARIO)
# ===============================
class ShulkerModal(discord.ui.Modal, title="Registro de Shulker"):
    cantidad = discord.ui.TextInput(
        label="¿Cuántas shulker colocaste?",
        placeholder="Ejemplo: 3",
        required=True,
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cantidad_int = int(self.cantidad.value)
            if cantidad_int <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ Debes ingresar un número válido mayor a 0.",
                ephemeral=True
            )
            return

        hoy = str(date.today())
        user_id = interaction.user.id
        username = interaction.user.display_name

        cursor.execute("""
            SELECT total FROM shulker
            WHERE user_id = ? AND fecha = ?
        """, (user_id, hoy))
        row = cursor.fetchone()

        if row:
            nuevo_total = row[0] + cantidad_int
            cursor.execute("""
                UPDATE shulker SET total = ?
                WHERE user_id = ? AND fecha = ?
            """, (nuevo_total, user_id, hoy))
        else:
            nuevo_total = cantidad_int
            cursor.execute("""
                INSERT INTO shulker (user_id, username, fecha, total)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, hoy, nuevo_total))

        db.commit()

        embed = discord.Embed(
            title="🧰 Aporte registrado",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=False)
        embed.add_field(name="📦 Shulker agregadas", value=str(cantidad_int), inline=False)
        embed.add_field(name="📊 Total hoy", value=str(nuevo_total), inline=False)

        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)

        await actualizar_ranking(interaction.client)

        await interaction.response.send_message(
            "✅ Registro guardado y ranking actualizado.",
            ephemeral=True
        )

# ===============================
# VISTA CON BOTÓN
# ===============================
class ShulkerButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Registrar Shulker",
        style=discord.ButtonStyle.green,
        emoji="📦",
        custom_id="registrar_shulker"
    )
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ShulkerModal())

# ===============================
# EVENTO READY (CON LIMPIEZA)
# ===============================
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

    channel = bot.get_channel(FORM_CHANNEL_ID)
    if not channel:
        return

    # 🧼 LIMPIAR MENSAJES ANTIGUOS DEL BOT
    async for message in channel.history(limit=50):
        if message.author == bot.user:
            await message.delete()

    # 📌 ENVIAR FORMULARIO ÚNICO
    await channel.send(
        embed=discord.Embed(
            title="🧰 Registro de Shulker",
            description="Presiona el botón para registrar cuántas shulker colocaste hoy.",
            color=discord.Color.green()
        ),
        view=ShulkerButton()
    )

# ===============================
# EJECUTAR BOT
# ===============================
bot.run(TOKEN)
