import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageOps
import os
import json
import random
import math

from draft_simulator import (
    load_cube_md,
    load_card_stats_from_json,
    build_card_pool,
    bot_pick,
    PACK_SIZE,
    NUM_ROUNDS,
    CUBE_MD_PATH,
    CARDS_JSON_PATH,
    DEFAULT_NUM_PLAYERS,
    initialize_bot_logs,
    get_bot_logs
)

CARD_IMAGE_PATH = 'cards'  # Base directory with images in /cards/<House>/<CardTitle>.png
ICONS_PATH = 'icons'

# Enhancement keys and icon filenames mapping
ENH_ORDER = [
    ('Enh.Amber', 'amber.png'),
    ('Enh.Capture', 'capture.png'),
    ('Enh.Draw', 'draw.png'),
    ('Enh.Damage', 'damage.png'),
    ('Enh.Discard', 'discard.png'),
]

class DraftUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CubeForge Draft Simulator")
        self.exported = False
        self.end_window = None

        # caches for PhotoImage objects
        self.photo_cache = {}
        self.icon_cache = {}

        # Load data
        self.cards = load_cube_md(CUBE_MD_PATH)
        self.card_pool, _ = build_card_pool(self.cards)
        self.stats, self.house_map = load_card_stats_from_json(CARDS_JSON_PATH)

        self.num_players = self.prompt_player_count()
        self.players = [[] for _ in range(self.num_players)]
        self.total_packs = self.num_players * NUM_ROUNDS

        initialize_bot_logs(self.num_players)

        # Pre-shuffle and prepare packs
        if len(self.card_pool) < self.total_packs * PACK_SIZE:
            messagebox.showerror("Error", "Not enough cards to run full draft.")
            self.root.destroy()
            return

        random.shuffle(self.card_pool)
        self.packs = [[self.card_pool.pop() for _ in range(PACK_SIZE)] for _ in range(self.total_packs)]

        self.round_index = 0
        self.pick_num = 0
        self.human_index = 0

        self.setup_ui()
        self.load_next_pack()

    def prompt_player_count(self):
        max_players = max(3, len(self.card_pool) // (PACK_SIZE * NUM_ROUNDS))
        self._max_players = max_players
        def submit():
            try:
                val = int(entry.get())
                if val < 3 or val > max_players:
                    raise ValueError
                count_window.destroy()
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.update()
                return val
            except:
                messagebox.showerror("Invalid Input", f"Enter a number between 3 and {max_players}.")

        self.root.withdraw()
        count_window = tk.Toplevel()
        count_window.geometry("300x150")
        count_window.title("Number of Players")
        tk.Label(count_window, text=f"Enter number of players (3–{self._max_players}):").pack(padx=10, pady=10)
        entry = tk.Entry(count_window)
        entry.pack(padx=10)
        entry.insert(0, str(DEFAULT_NUM_PLAYERS))
        tk.Button(count_window, text="Start", command=lambda: setattr(self, '_player_count', submit())).pack(pady=10)
        self.root.wait_window(count_window)
        return getattr(self, '_player_count', DEFAULT_NUM_PLAYERS)

    def setup_ui(self):
        self.left_panel = tk.Frame(self.root)
        self.left_panel.pack_propagate(False)
        self.left_panel.pack(side=tk.LEFT, padx=10, pady=10, fill="both", expand=True)

        self.right_panel = tk.Frame(self.root, width=300, height=400)
        self.right_panel.pack(side=tk.RIGHT, padx=10, pady=10, fill="y", expand=False)

        self.title_label = tk.Label(self.left_panel, text=f"Your Pack - Pick {self.pick_num + 1}, Round {self.round_index + 1}", font=("Arial", 16))
        self.title_label.pack()

        self.pack_frame = tk.Frame(self.left_panel)
        self.pack_frame.pack(fill="both", expand=False)

        self.draft_label = tk.Label(self.right_panel, text="Your Picks", font=("Arial", 16))
        self.draft_label.pack()

        # Scrollable area for picks
        container = tk.Frame(self.right_panel)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, height=500)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.picks_frame = tk.Frame(canvas)

        self.picks_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.picks_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.pick_images = []

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.picks_frame.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.picks_frame.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        self.picks_canvas = canvas

    def load_icon(self, filename, size=(20,20)):
        path = os.path.join(ICONS_PATH, filename)
        key = (path, size)
        if key in self.icon_cache:
            return self.icon_cache[key]
        try:
            img = Image.open(path).convert('RGBA')
            img = ImageOps.contain(img, size)
            photo = ImageTk.PhotoImage(img)
        except Exception:
            img = Image.new('RGBA', size, (180,180,180,255))
            photo = ImageTk.PhotoImage(img)
        self.icon_cache[key] = photo
        return photo

    def overlay_icons_on_card(self, card_img, card_data, icon_size=15):
        card_width, card_height = card_img.size
        x_pos = int(card_width * 0.067)
        y_start = int(card_height * 0.198)

        def to_int(v):
            try:
                return int(v)
            except:
                return 0

        printed_amber = to_int(card_data.get('amber', 0))
        enh_counts = {k: to_int(card_data.get(k, 0)) for k, _ in ENH_ORDER}

        # Skip space for printed amber
        y_offset = y_start + printed_amber * (icon_size + 2)

        # Amber enhancements first
        for _ in range(enh_counts.get('Enh.Amber', 0)):
            icon_img = Image.open(os.path.join(ICONS_PATH, 'amber.png')).convert('RGBA').resize((icon_size, icon_size))
            card_img.paste(icon_img, (x_pos, y_offset), icon_img)
            y_offset += icon_size + 2

        # Other enhancements
        for enh_key, icon_file in ENH_ORDER:
            if enh_key == 'Enh.Amber':
                continue
            for _ in range(enh_counts.get(enh_key, 0)):
                icon_img = Image.open(os.path.join(ICONS_PATH, icon_file)).convert('RGBA').resize((icon_size, icon_size))
                card_img.paste(icon_img, (x_pos, y_offset), icon_img)
                y_offset += icon_size + 2

        return card_img

    def get_card_image_with_icons(self, house, title, card_data, size=(180, 252), icon_size=15):
        sanitized_name = title.replace("'", "").replace(" ", "_").replace(":", "")
        image_path = os.path.join(CARD_IMAGE_PATH, house, f"{sanitized_name}.png")
        try:
            card_img = Image.open(image_path).convert('RGBA').resize(size)
        except:
            card_img = Image.new('RGBA', size, (128, 128, 128, 255))
        card_img = self.overlay_icons_on_card(card_img, card_data, icon_size=icon_size)
        return ImageTk.PhotoImage(card_img)

    def load_next_pack(self):
        if self.pick_num >= PACK_SIZE:
            self.round_index += 1
            self.pick_num = 0
            if self.round_index >= NUM_ROUNDS:
                self.finish_draft()
                return

        round_packs = [
            self.packs[self.round_index * self.num_players + i]
            for i in range(self.num_players)
        ]

        self.direction = 1 if self.round_index % 2 == 0 else -1

        self.current_pack = round_packs[(self.human_index + self.pick_num * self.direction) % self.num_players]
        self.title_label.config(text=f"Pack {self.round_index + 1} - Pick {self.pick_num + 1}")
        if self.round_index >= NUM_ROUNDS:
            for widget in self.pack_frame.winfo_children():
                widget.destroy()
            return
        self.render_pack()

    def render_pack(self):
        for widget in self.pack_frame.winfo_children():
            widget.destroy()

        for idx, card in enumerate(self.current_pack):
            if isinstance(card, dict):
                title = card.get('CardTitle', '')
                house = card.get('House', self.house_map.get(title, 'Unknown'))
            else:
                title = str(card)
                house = self.house_map.get(title, 'Unknown')
                card = {'CardTitle': title, 'House': house}

            photo = self.get_card_image_with_icons(house, title, card)
            frame = tk.Frame(self.pack_frame)
            frame.grid(row=idx // 4, column=idx % 4, padx=8, pady=8)

            btn = tk.Button(frame, image=photo, command=lambda i=idx: self.pick_card(i))
            btn.image = photo
            btn.pack()

    def pick_card(self, index):
        if not self.current_pack or index >= len(self.current_pack):
            return
        pick = self.current_pack.pop(index)
        self.players[0].append(pick)

        picked_title = pick.get('CardTitle') if isinstance(pick, dict) else pick
        house = self.house_map.get(picked_title, "Unknown")
        if house == "Unknown":
            print(f"[DEBUG] Human picked unknown card: '{picked_title}'")

        for i in range(1, self.num_players):
            bot_pack = self.packs[self.round_index * self.num_players + ((i + self.pick_num * self.direction) % self.num_players)]
            bot_pick_result = bot_pick(bot_pack, self.players[i], self.stats, self.house_map, i)

            bot_title = bot_pick_result.get('CardTitle') if isinstance(bot_pick_result, dict) else bot_pick_result
            house = self.house_map.get(bot_title, "Unknown")
            if house == "Unknown":
                print(f"[DEBUG] Bot {i} picked unknown card: '{bot_title}'")

            bot_pack.remove(bot_pick_result)
            self.players[i].append(bot_pick_result)

        self.pick_num += 1
        self.update_drafted()
        self.load_next_pack()

    def update_drafted(self):
        for widget in self.picks_frame.winfo_children():
            widget.destroy()
        self.pick_images.clear()

        house_grouped = {}
        for card in self.players[0]:
            title = card.get('CardTitle') if isinstance(card, dict) else card
            house = self.house_map.get(title, 'Unknown')
            house_grouped.setdefault(house, []).append(card)

        for house, cards in house_grouped.items():
            label = tk.Label(self.picks_frame, text=f"[{house}] ({len(cards)})", font=("Arial", 12, "bold"))
            label.pack()
            row_frame = tk.Frame(self.picks_frame)
            row_frame.pack(anchor='w', fill='x')
            max_per_row = 3
            for i in range(0, len(cards), max_per_row):
                row = tk.Frame(row_frame)
                row.pack(anchor='w')
                for c in cards[i:i+max_per_row]:
                    title = c.get('CardTitle') if isinstance(c, dict) else c
                    san = title.replace(" ", "_").replace("'", "").replace(":", "")
                    image_path = os.path.join(CARD_IMAGE_PATH, house, f"{san}.png")
                    try:
                        card_img = Image.open(image_path).convert('RGBA').resize((90, 126))
                    except:
                        card_img = Image.new('RGBA', (90, 126), (128, 128, 128, 255))
                    card_img = self.overlay_icons_on_card(card_img, c, icon_size=7)
                    photo = ImageTk.PhotoImage(card_img)
                    lbl = tk.Label(row, image=photo)
                    lbl.image = photo
                    lbl.pack(side=tk.LEFT, padx=2)
                    self.pick_images.append(photo)

    def finish_draft(self):
        self.update_drafted()

        if self.end_window is not None and self.end_window.winfo_exists():
            self.end_window.lift()
            self.end_window.attributes('-topmost', True)
            self.end_window.attributes('-topmost', False)
            return

        from uuid import uuid4
        uid = uuid4().hex[:8]

        with open(f"bot_picks_log_{uid}.json", "w", encoding="utf-8") as f:
            json.dump(get_bot_logs(), f, indent=2, ensure_ascii=False)

        def export_json():
            if self.exported:
                return

            filename = f"draft_results_{uid}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({
                    f"Player {i+1}": [{"id": idx + 1, "card": (c.get('CardTitle') if isinstance(c, dict) else c)} for idx, c in enumerate(picks)]
                    for i, picks in enumerate(self.players)
                }, f, indent=2, ensure_ascii=False)

            self.exported = True
            if self.end_window and self.end_window.winfo_exists():
                self.end_window.destroy()
                self.end_window = None
            messagebox.showinfo("Exported", f"Draft results saved to {filename}")
            self.finish_draft()

        def restart():
            self.root.destroy()
            import subprocess
            subprocess.Popen(['python', __file__])

        self.update_drafted()

        self.end_window = tk.Toplevel(self.root)
        self.end_window.title("Draft Complete")
        tk.Label(self.end_window, text="Draft complete! What would you like to do?").pack(padx=10, pady=10)
        export_btn = tk.Button(self.end_window, text="Export JSON", command=export_json)
        export_btn.pack(pady=5)
        if self.exported:
            export_btn.config(state=tk.DISABLED)
        tk.Button(self.end_window, text="Restart Draft", command=restart).pack(pady=5)
        tk.Button(self.end_window, text="Exit", command=self.root.quit).pack(pady=5)

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("1400x900")
    app = DraftUI(root)
    root.mainloop()