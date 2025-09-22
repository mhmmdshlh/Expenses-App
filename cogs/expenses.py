import discord
from discord.ext import commands
from expense_manager import ExpenseManager
from sync_drive import get_file, upload_file
from dotenv import load_dotenv
import os
from datetime import datetime
import re

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
data_dir = os.path.join(BASE_DIR, "data")
os.makedirs(data_dir, exist_ok=True)
db_path = os.path.join(data_dir, "expenses.db")

class ExpenseView(discord.ui.View):
    def __init__(self, db: ExpenseManager, initial_filters: dict = None):
        super().__init__(timeout=180)
        self.db = db
        self.filters = initial_filters or {}
        self.current_page = 0
        self.items_per_page = 5
        self.sort_by = 'date'
        self.sort_desc = True
        self.view_mode = 'detail'  # 'detail' atau 'summary'
        self.message = None
        
        # Inisialisasi pages
        df = self.db.fetch(filters=self.filters, desc=self.sort_desc)
        self.pages = self.create_embed(df)
        self.update_button_states()
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
            
        if self.message and self.message.embeds:
            embed = self.message.embeds[0]
            embed.color = discord.Color.red()
            await self.message.edit(content="Paginator expired ⌛", embed=embed, view=self)
        
    def create_embed(self, df):
        if df.empty:
            embed = discord.Embed(
                title="📊 Expenses",
                description="Tidak ada data yang ditemukan",
                color=discord.Color.blue()
            )
            return [embed]
            
        embeds = []
        # Summary embed
        if self.view_mode == 'summary':
            summary_embed = discord.Embed(
                title="📊 Ringkasan Pengeluaran",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            # Statistik dasar
            summary = (f"💰 Total: Rp{df['price'].sum():,}\n"
                    f"📊 Rata-rata: Rp{int(df['price'].mean()):,}\n"
                    f"📈 Tertinggi: Rp{df['price'].max():,}\n"
                    f"📉 Terendah: Rp{df['price'].min():,}\n"
                    f"🔢 Jumlah transaksi: {len(df)}")
            summary_embed.add_field(name="Statistik", value=summary, inline=False)
            
            # Ringkasan per kategori
            cat_summary = df.groupby('category_name').agg({
                'price': ['count', 'sum', 'mean']
            }).reset_index()
            
            cat_summary.columns = ['category_name', 'count', 'total', 'average']
            
            for _, row in cat_summary.iterrows():
                value = (f"📝 Jumlah: {row['count']}\n"
                        f"💰 Total: Rp{row['total']:,}\n"
                        f"📊 Rata-rata: Rp{int(row['average']):,}")
                summary_embed.add_field(
                    name=f"📁 {row['category_name']}", 
                    value=value, 
                    inline=True
                )
            
            embeds.append(summary_embed)
        
        # Detail embeds
        elif self.view_mode == 'detail':
            chunks = [df.iloc[i:i + self.items_per_page] 
                     for i in range(0, len(df), self.items_per_page)]
            
            for i, chunk in enumerate(chunks, 1):
                embed = discord.Embed(
                    title="📋 Detail Pengeluaran",
                    description=f"Halaman {i} dari {len(chunks)}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                for _, row in chunk.iterrows():
                    harga = f"Rp{row['price']:,}"
                    embed.add_field(
                        name=f"[{row['id']}] {row['item']} - {harga}",
                        value=f"📆 {row['date']} | 🏷️ {row['category_name']}",
                        inline=False
                    )
                
                embeds.append(embed)
        
        return embeds
        
    def update_button_states(self):
        if self.view_mode == 'summary':
            for child in self.children:
                if child != self.toggle_view:
                    child.disabled = True
        else:
            self.first.disabled = self.current_page == 0
            self.previous.disabled = self.current_page == 0
            self.next.disabled = self.current_page >= len(self.pages) - 1
            self.last.disabled = self.current_page >= len(self.pages) - 1
            self.period_select.disabled = False
            self.toggle_sort_date.disabled = False
            self.toggle_sort_price.disabled = False

        self.toggle_view.disabled = False

    async def update_view(self, interaction: discord.Interaction):
        try:
            df = self.db.fetch(
                filters=self.filters,
                orderby=self.sort_by,
                desc=self.sort_desc
            )
            self.pages = self.create_embed(df)
            
            if self.current_page >= len(self.pages):
                self.current_page = len(self.pages) - 1 if len(self.pages) > 0 else 0
                
            self.update_button_states()
                
            # Update the view
            if interaction.response.is_done():
                await interaction.message.edit(
                    embed=self.pages[self.current_page] if self.pages else discord.Embed(
                        title="📊 Expenses",
                        description="Tidak ada data yang ditemukan",
                        color=discord.Color.blue()
                    ),
                    view=self
                )
            else:
                await interaction.response.edit_message(
                    embed=self.pages[self.current_page] if self.pages else discord.Embed(
                        title="📊 Expenses",
                        description="Tidak ada data yang ditemukan",
                        color=discord.Color.blue()
                    ),
                    view=self
                )
        except Exception as e:
            try:
                content = f"Terjadi kesalahan: {str(e)}"
                if interaction.response.is_done():
                    await interaction.followup.send(content, ephemeral=True)
                else:
                    await interaction.response.send_message(content, ephemeral=True)
            except:
                print(f"Error in update_view: {e}")

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.primary)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await self.update_view(interaction)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_view(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        await self.update_view(interaction)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.primary)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        await self.update_view(interaction)
        
    @discord.ui.button(label="🔄", style=discord.ButtonStyle.success, row=1)
    async def toggle_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.view_mode = 'summary' if self.view_mode == 'detail' else 'detail'
        self.current_page = 0
        await self.update_view(interaction)
        
    @discord.ui.select(
        placeholder="Pilih Periode",
        options=[
            discord.SelectOption(label="Hari Ini", value="today"),
            discord.SelectOption(label="Minggu Ini", value="this_week"),
            discord.SelectOption(label="Bulan Ini", value="this_month"),
            discord.SelectOption(label="Tahun Ini", value="this_year"),
            discord.SelectOption(label="Semua", value="all")
        ],
        row=2
    )
    async def period_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        today = datetime.now()
        
        if select.values[0] == "today":
            self.filters = {
                'year': [today.strftime('%Y')],
                'month': [today.strftime('%m')],
                'day': [today.strftime('%d')]
            }
        elif select.values[0] == "this_month":
            self.filters = {
                'year': [today.strftime('%Y')],
                'month': [today.strftime('%m')]
            }
        elif select.values[0] == "this_year":
            self.filters = {
                'year': [today.strftime('%Y')]
            }
        else:
            self.filters = {}
            
        self.current_page = 0
        await self.update_view(interaction)
        
    @discord.ui.button(label="📅", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_sort_date(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.sort_by == 'date':
            self.sort_desc = not self.sort_desc
        else:
            self.sort_by = 'date'
            self.sort_desc = True
        await self.update_view(interaction)
        
    @discord.ui.button(label="💰", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_sort_price(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.sort_by == 'price':
            self.sort_desc = not self.sort_desc
        else:
            self.sort_by = 'price'
            self.sort_desc = True
        await self.update_view(interaction)

class DeleteConfirmationView(discord.ui.View):
    def __init__(self, db: ExpenseManager, to_delete: list, existing_records, not_found: list):
        super().__init__(timeout=30)
        self.db = db
        self.to_delete = to_delete
        self.existing_records = existing_records
        self.not_found = not_found
        self.message = None
        
    async def on_timeout(self):
        for child in self.children: 
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await self.message.edit(content="❌ Waktu konfirmasi habis. Penghapusan dibatalkan.", embed=embed, view=self)
    
    @discord.ui.button(label="✅ Ya", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.defer()
        
        # Process deletion
        succ = []
        fail = []
        for expense_id in self.to_delete:
            try:
                if self.db.delete_data(expense_id):
                    succ.append(str(expense_id))
            except (ExpenseManager.InvalidInputError, ExpenseManager.DatabaseOperationError) as e:
                fail.append(f"{expense_id} ({e})")

        # Prepare result message
        messages = []
        if succ:
            messages.append(f"✅ Data dengan ID {', '.join(succ)} berhasil dihapus!")
        if fail:
            messages.append(f"❌ Gagal menghapus: {', '.join(fail)}")
        if self.not_found:
            messages.append(f"❓ ID tidak ditemukan: {', '.join(self.not_found)}")

        embed = self.message.embeds[0]
        embed.color = discord.Color.green()
        await interaction.message.edit(content='\n'.join(messages), view=self, embed=embed)
        self.stop()
        
    @discord.ui.button(label="❌ Tidak", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await interaction.response.edit_message(content="❌ Penghapusan dibatalkan.", embed=embed, view=self)
        self.stop()

class CategoryUpdateView(discord.ui.View):
    def __init__(self, db: ExpenseManager, old_name: str, new_name: str):
        super().__init__(timeout=30)
        self.db = db
        self.old_name = old_name
        self.new_name = new_name
        self.affected_records = None
        self.message = None
        
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await self.message.edit(content="⌛ Waktu habis! Perubahan dibatalkan.", embed=embed, view=self)
    
    @discord.ui.button(label="✅ Ya", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
            
        if self.db.update_category_name(self.old_name, self.new_name):
            embed = discord.Embed(
                title="✅ Kategori Berhasil Diubah",
                description=f"Kategori `{self.old_name}` telah diubah menjadi `{self.new_name}`\n"
                          f"Mempengaruhi {len(self.affected_records)} data.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed = discord.Embed(
                title="❌ Gagal Mengubah Kategori",
                description="Terjadi kesalahan saat mengubah nama kategori.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
        
    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await interaction.response.edit_message(content="❌ Perubahan dibatalkan.", embed=embed, view=self)
        self.stop()

class AddManyConfirmView(discord.ui.View):
    def __init__(self, db: ExpenseManager, entries: list):
        super().__init__(timeout=60)
        self.db = db
        self.entries = entries
        self.message = None
        
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await self.message.edit(content="⌛ Waktu habis! Penambahan data dibatalkan.", embed=embed, view=self)
    
    @discord.ui.button(label="✅ Ya", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        
        success = []
        failed = []
        
        for entry in self.entries:
            try:
                date, item, price, cat = entry['date'], entry['item'], entry['price'], entry['category']
                if self.db.add(date, item, price, cat):
                    success.append(item)
                else:
                    failed.append(f"{item} (unknown error)")
            except Exception as e:
                failed.append(f"{item} ({str(e)})")
        
        embed = discord.Embed(
            title="📝 Hasil Penambahan Data",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if success:
            embed.add_field(
                name="✅ Berhasil Ditambahkan",
                value="\n".join([f"• {item}" for item in success]),
                inline=False
            )
        
        if failed:
            embed.add_field(
                name="❌ Gagal Ditambahkan",
                value="\n".join([f"• {item}" for item in failed]),
                inline=False
            )
            
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
        
    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await interaction.response.edit_message(content="❌ Penambahan data dibatalkan.", embed=embed, view=self)
        self.stop()

class AddConfirmationView(discord.ui.View):
    def __init__(self, db: ExpenseManager, date: str, item: str, price: int, category: str):
        super().__init__(timeout=30) 
        self.db = db
        self.date = date
        self.item = item
        self.price = price
        self.category = category
        self.message = None
        
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await self.message.edit(content="⌛ Timeout! Addition cancelled.", embed=embed, view=self)
    
    @discord.ui.button(label="✅ Add", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
            
        try:
            if self.db.add(self.date, self.item, self.price, self.category):
                embed = discord.Embed(
                    title="✅ Expense Added Successfully",
                    description=f"Added {self.item} (Rp{self.price:,})",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="📅 Date", value=self.date, inline=True)
                embed.add_field(name="🏷️ Category", value=self.category, inline=True)
            else:
                embed = discord.Embed(
                    title="❌ Failed to Add Expense",
                    description="Unknown error occurred",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=str(e),
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()
        
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        await interaction.response.edit_message(content="❌ Addition cancelled.", embed=embed, view=self)
        self.stop()

class Expense(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = ExpenseManager(db_path)
    
    def cog_check(self, ctx):
        return ctx.channel.id == int(os.getenv('EXPENSES_CHANNEL_ID')) and ctx.prefix == '>'

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("Perintah ini hanya bisa digunakan di channel dan dengan prefix yang sudah ditentukan.", delete_after=10)
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if isinstance(original, (ExpenseManager.InvalidInputError, ExpenseManager.DatabaseOperationError)):
                await ctx.send(f"Terjadi kesalahan: {original}")
            else:
                await ctx.send("Terjadi kesalahan internal saat menjalankan perintah.")
                print(f"Unhandled error in command {ctx.command}: {original}")
        else:
            await super().cog_command_error(ctx, error)
    
    @commands.command()
    async def save(self, ctx):
        """Save the database to cloud storage.
        
        Shows sync status and last backup timestamp.
        """
        embed = discord.Embed(
            title="💾 Saving Database...",
            description="Uploading to cloud storage...",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        msg = await ctx.send(embed=embed)
        
        try:
            upload_file('expenses.db', db_path)
            embed.title = "✅ Database Saved!"
            embed.description = "Successfully backed up to cloud storage."
            embed.add_field(
                name="Last Sync",
                value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                inline=False
            )
            embed.color = discord.Color.green()
        except Exception as e:
            embed.title = "❌ Save Failed!"
            embed.description = f"Error: {str(e)}"
            embed.color = discord.Color.red()
        
        await msg.edit(embed=embed)
    
    @commands.command()
    async def load(self, ctx):
        """Load the database from cloud storage.
        
        Shows sync status and recovery timestamp.
        """
        embed = discord.Embed(
            title="📥 Loading Database...",
            description="Downloading from cloud storage...",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        msg = await ctx.send(embed=embed)
        
        try:
            get_file('expenses.db', db_path)
            embed.title = "✅ Database Loaded!"
            embed.description = "Successfully restored from cloud storage."
            embed.add_field(
                name="Recovery Time",
                value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                inline=False
            )
            embed.color = discord.Color.green()
        except Exception as e:
            embed.title = "❌ Load Failed!"
            embed.description = f"Error: {str(e)}"
            embed.color = discord.Color.red()
        
        await msg.edit(embed=embed)

    @commands.command()
    async def add(self, ctx, date: str, item: str, price: str, category: str):
        """Add a new expense record.
        
        Shows preview and confirmation before adding.
        Price can use dots as thousand separators.
        
        Usage:
            >add YYYY-MM-DD item price category
        
        Examples:
            >add 2025-09-17 Lunch 25.000 Food
            >add 2025-09-17 Gas 50000 Transport
        """
        # Validate date format
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d')
            if parsed_date > datetime.now():
                await ctx.send("❌ Cannot add future dates!", delete_after=5)
                return
        except ValueError:
            await ctx.send("❌ Invalid date format. Use YYYY-MM-DD", delete_after=5)
            return

        # Validate price
        try:
            price_clean = int(price.replace('.', ''))
            if price_clean <= 0:
                await ctx.send("❌ Price must be greater than 0!", delete_after=5)
                return
        except ValueError:
            await ctx.send("❌ Invalid price format. Use numbers only (with optional dots)", delete_after=5)
            return
            
        # Create preview embed
        embed = discord.Embed(
            title="📝 Preview Data Baru",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📅 Date", value=date, inline=True)
        embed.add_field(name="📌 Item", value=item, inline=True)
        embed.add_field(name="💰 Price", value=f"Rp{price_clean:,}", inline=True)
        embed.add_field(name="🏷️ Category", value=category, inline=True)

        # Send confirmation view
        view = AddConfirmationView(self.db, date, item, price_clean, category)
        view.message = await ctx.send(embed=embed, view=view)
        await view.wait()

    @commands.command(name='a')
    async def special_add(self, ctx, *, text):
        pola_tanggal = r"(\d{2}/\d{2}/\d{4})"
        pola_item = r"- ([\d\.]+) \((.+)\) (.+)"
        match_tanggal = re.search(pola_tanggal, text)
        if not match_tanggal:
            await ctx.send("Format tanggal tidak ditemukan. Gunakan `dd/mm/YYYY` di pesan.", delete_after=8)
            return

        items_found = re.findall(pola_item, text)
        if not items_found:
            await ctx.send("Tidak ada item yang dikenali. Pastikan format item: `- 25.000 (Kategori) Nama Item`", delete_after=8)
            return

        tanggal = match_tanggal.group(1)
        date = datetime.strptime(tanggal, '%d/%m/%Y').strftime('%Y-%m-%d')

        added = []
        errors = []
        for price_s, cat, item in items_found:
            try:
                price = int(price_s.replace('.', ''))
            except ValueError:
                errors.append(f"{item}: harga '{price_s}' tidak valid")
                continue

            try:
                if self.db.add(date, item, price, cat):
                    added.append(item)
            except ExpenseManager.InvalidInputError as e:
                errors.append(f"{item}: input tidak valid ({e})")
            except ExpenseManager.DatabaseOperationError as e:
                errors.append(f"{item}: DB error ({e})")

        if added:
            await ctx.send("Berhasil menambahkan: " + ", ".join(added))
        if errors:
            await ctx.send("Beberapa item gagal ditambahkan:\n" + "\n".join(errors))
            
    @commands.command()
    async def addmany(self, ctx, *, args):
        """Add multiple expense records at once.
        
        This command will show a preview and confirmation view before adding the records.
        Supports adding multiple entries separated by commas.
        The operation will timeout after 60 seconds if not confirmed.
        
        Format:
            >addmany date item price category, date item price category, ...
            
        Requirements:
            - Date must be in YYYY-MM-DD format
            - Price can use dots as thousand separators (15.000)
            - Each entry must be separated by commas
            
        Examples:
            >addmany 2025-09-17 Snack 15000 Food
            >addmany 2025-09-17 Snack 15.000 Food, 2025-09-17 Gas 50.000 Transport
        """
        entries = []
        invalid = []
        
        for entry in args.split(','):
            try:
                parts = entry.strip().split()
                if len(parts) < 4:
                    raise ValueError("format harus: <date> <item> <price> <category>")
                    
                date, item, price_s, cat = parts[0], parts[1], parts[2], parts[3]
                
                # Validate date format
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    if date_obj > datetime.now():
                        raise ValueError("Cannot add future dates!", delete_after=5)
                except ValueError:
                    raise ValueError(f"format tanggal salah: {date} (gunakan YYYY-MM-DD)")
                
                # Validate price
                try:
                    price = int(price_s.replace('.', ''))
                except ValueError:
                    raise ValueError(f"harga tidak valid: {price_s}")
                
                entries.append({
                    'date': date,
                    'item': item,
                    'price': price,
                    'category': cat
                })
            except Exception as e:
                invalid.append(f"• {entry.strip()}\n  ↳ Error: {str(e)}")
        
        if invalid:
            error_msg = "❌ Beberapa data tidak valid:\n" + "\n".join(invalid)
            await ctx.send(error_msg)
            if not entries:
                return
                
        # Create preview embed
        embed = discord.Embed(
            title="📝 Preview Data yang Akan Ditambahkan",
            description=f"Total {len(entries)} data akan ditambahkan.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for entry in entries:
            embed.add_field(
                name=f"📌 {entry['item']}",
                value=f"💰 Rp{entry['price']:,}\n"
                      f"📅 {entry['date']}\n"
                      f"🏷️ {entry['category']}",
                inline=True
            )
            
        # Send confirmation view
        view = AddManyConfirmView(self.db, entries)
        view.message = await ctx.send(embed=embed, view=view)
        
        # Wait for interaction
        await view.wait()
    
    @commands.command()
    async def view(self, ctx, *args):
        """View expense records with an interactive UI.
        
        Usage:
            >view [filter=value]
            
        Available Filters:
            year=YYYY         - Filter by year
            month=MM         - Filter by month
            day=DD           - Filter by day
            cat=category     - Filter by category
            
        Examples:
            >view                    - Show current month
            >view month=09          - Show September expenses
            >view year=2025        - Show entire year
            >view cat=Food         - Show expenses by category
        """
        # Parse arguments
        filters = {
            'year': [], 'month': [], 'day': [], 
            'category_name': []
        }

        for arg in args:
            try:
                if '=' not in arg:
                    await ctx.send("❌ Format tidak valid. Gunakan format `filter=value`", delete_after=8)
                    return
                    
                key, val = arg.split('=')
                key = key.lower()
                
                if not val:
                    await ctx.send(f"❌ Nilai untuk filter '{key}' tidak boleh kosong!", delete_after=8)
                    return

                if key == 'cat':
                    filters['category_name'].extend(val.split(','))
                elif key in filters:
                    for v in val.split(','):
                        if v.isdigit():
                            filters[key].append(v.zfill(2) if key in ['month', 'day'] else v)
                        else:
                            await ctx.send(f"❌ Nilai '{v}' tidak valid untuk filter '{key}'!", delete_after=8)
                            return
                else:
                    await ctx.send(f"❌ Filter '{key}' tidak dikenal!", delete_after=8)
                    return
                    
            except ValueError:
                await ctx.send('❌ Format tidak valid. Contoh: `>view month=09`', delete_after=8)
                return

        # Set default filters for current month if no date filters specified
        if not any(filters[k] for k in ['year', 'month', 'day']):
            last_date = self.db.last_date
            if last_date is None:
                await ctx.send('❌ No data found in database.', delete_after=8)
                return
            filters['year'] = [last_date.strftime('%Y')]
            filters['month'] = [last_date.strftime('%m')]

        try:
            view = ExpenseView(self.db, filters)
            
            if not view.pages:
                await ctx.send('❌ Tidak ada data yang ditemukan!')
                return
                
            message = await ctx.send(embed=view.pages[0], view=view)
            view.message = message
        except Exception as e:
            await ctx.send(f"❌ Terjadi kesalahan: {str(e)}")

    @commands.command()
    async def delete(self, ctx, *args):
        """Delete expense records by their IDs.
        
        This command will show a confirmation view before deletion.
        The operation will timeout after 30 seconds if not confirmed.
        
        Usage:
            >delete id1 [id2 id3 ...]
            
        Examples:
            >delete 1             - Delete single record
            >delete 1 2 3         - Delete multiple records
        """
        if not args:
            await ctx.send("❌ Masukkan ID yang ingin dihapus. Contoh: `>delete 1 2 3`", delete_after=8)
            return

        # First validate all IDs
        invalid_ids = [id_str for id_str in args if not id_str.isdigit() or int(id_str) <= 0]
        if invalid_ids:
            await ctx.send(f"❌ ID tidak valid: {', '.join(invalid_ids)}", delete_after=8)
            return

        ids = [int(id_str) for id_str in args]
        
        # Get existing records first to verify they exist
        existing_records = self.db.fetch(filters={'id': ids})
        existing_ids = existing_records['id'].tolist()
        
        not_found = [str(id) for id in ids if id not in existing_ids]
        to_delete = [id for id in ids if id in existing_ids]

        if not to_delete:
            await ctx.send("❌ Tidak ada ID yang valid untuk dihapus.", delete_after=8)
            return

        embed = discord.Embed(
            title="🗑️ Konfirmasi Penghapusan",
            description="Apakah Anda yakin ingin menghapus data berikut?",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for _, row in existing_records.iterrows():
            embed.add_field(
                name=f"ID {row['id']}: {row['item']}",
                value=f"💰 Rp{row['price']:,}\n📅 {row['date']}\n🏷️ {row['category_name']}",
                inline=True
            )

        view = DeleteConfirmationView(self.db, to_delete, existing_records, not_found)
        view.message = await ctx.send(embed=embed, view=view)
        
        await view.wait()
    
    @commands.command()
    async def upcatname(self, ctx, old_name, new_name):
        """Update a category name for all expense records.
        
        This command will show affected records preview and confirmation view.
        Shows statistics about how many records will be affected.
        The operation will timeout after 30 seconds if not confirmed.
        
        Usage:
            >upcatname <old_name> <new_name>
            
        Examples:
            >upcatname Food Meals
            >upcatname Transport Transportation
        """
        df = self.db.fetch(filters={'category_name': [old_name]})
        if df.empty:
            await ctx.send(f"❌ Kategori `{old_name}` tidak ditemukan!")
            return
            
        embed = discord.Embed(
            title="📝 Preview Perubahan Kategori",
            description=f"Mengubah kategori `{old_name}` menjadi `{new_name}`",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add statistics
        total_amount = df['price'].sum()
        affected_count = len(df)
        
        embed.add_field(
            name="📊 Statistik",
            value=f"🔢 Jumlah data: {affected_count}\n"
                  f"💰 Total: Rp{total_amount:,}",
            inline=False
        )
        
        # Add sample data
        sample = df.head(3)
        samples = []
        for _, row in sample.iterrows():
            samples.append(f"• {row['item']} (Rp{row['price']:,})")
        
        if not df.empty:
            embed.add_field(
                name="📋 Contoh Data",
                value="\n".join(samples) + 
                      ("\n..." if len(df) > 3 else ""),
                inline=False
            )
            
        view = CategoryUpdateView(self.db, old_name, new_name)
        view.affected_records = df
        view.message = await ctx.send(embed=embed, view=view)
        
        await view.wait()

async def setup(bot):
    await bot.add_cog(Expense(bot))
