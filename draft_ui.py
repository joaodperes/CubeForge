import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import json

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

CARD_IMAGE_PATH = 'cards'  # Base directory with images in /cards/<House>/<CardTitle>.jpg

class DraftUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Cube Draft Simulator")
        self.exported = False
        self.end_window = None

        # Load data
        self.cards = load_cube_md(CUBE_MD_PATH)
        self.card_pool, _ = build_card_pool(self.cards)
        self.stats, self.house_map = load_card_stats_from_json(CARDS_JSON_PATH)

        self.num_players = self.prompt_player_count()
        self.players = [[] for _ in range(self.num_players)]
        self.total_packs = self.num_players * NUM_ROUNDS

        # after self.num_players is set in DraftUI.__init__ or wherever
        initialize_bot_logs(self.num_players)

        # Pre-shuffle and prepare packs
        if len(self.card_pool) < self.total_packs * PACK_SIZE:
            messagebox.showerror("Error", "Not enough cards to run full draft.")
            self.root.destroy()
            return

        import random
        random.shuffle(self.card_pool)
        self.packs = [[self.card_pool.pop() for _ in range(PACK_SIZE)] for _ in range(self.total_packs)]

        self.round_index = 0
        self.pick_num = 0
        self.human_index = 0

        self.setup_ui()
        self.load_next_pack()

    def prompt_player_count(self):
        import math
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
        self.left_panel = tk.Frame(self.root, width=700, height=400)
        self.left_panel.pack_propagate(False)
        self.left_panel.pack(side=tk.LEFT, padx=10, pady=10)

        self.right_panel = tk.Frame(self.root, width=300, height=400)
        self.right_panel.pack_propagate(False)
        self.right_panel.pack(side=tk.RIGHT, padx=10, pady=10)

        self.title_label = tk.Label(self.left_panel, text=f"Your Pack - Pick {self.pick_num + 1}, Round {self.round_index + 1}", font=("Arial", 16))
        self.title_label.pack()

        self.pack_frame = tk.Frame(self.left_panel)
        self.pack_frame.pack()

        self.draft_label = tk.Label(self.right_panel, text="Your Picks", font=("Arial", 16))
        self.draft_label.pack()

        # Scrollable area
        container = tk.Frame(self.right_panel)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, height=300)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.picks_frame = tk.Frame(canvas)

        self.picks_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.picks_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.pick_images = []

        # Mousewheel scroll binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Bind mousewheel when mouse is over the picks frame
        self.picks_frame.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.picks_frame.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        # Save canvas reference
        self.picks_canvas = canvas

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
            sanitized_name = card.replace("'", "").replace(" ", "_")
            image_path = os.path.join(CARD_IMAGE_PATH, self.house_map.get(card, "Unknown"), f"{sanitized_name}.png")
            try:
                img = Image.open(image_path).resize((120, 168))
                photo = ImageTk.PhotoImage(img)
            except:
                photo = ImageTk.PhotoImage(Image.new('RGB', (120, 168), color='gray'))

            btn = tk.Button(self.pack_frame, image=photo, command=lambda i=idx: self.pick_card(i))
            btn.image = photo  # keep a reference
            btn.grid(row=idx // 5, column=idx % 5, padx=5, pady=5)

    def pick_card(self, index):
        if not self.current_pack or index >= len(self.current_pack):
            return  # Prevent pop from empty list or out-of-range
        pick = self.current_pack.pop(index)
        self.players[0].append(pick)

        # Debugging: check if pick has unknown house
        house = self.house_map.get(pick, "Unknown")
        if house == "Unknown":
            print(f"[DEBUG] Human picked unknown card: '{pick}' (not found in cards.json)")

        for i in range(1, self.num_players):
            bot_pack = self.packs[self.round_index * self.num_players + ((i + self.pick_num * self.direction) % self.num_players)]
            bot_pick_result = bot_pick(bot_pack, self.players[i], self.stats, self.house_map, i)
            
            # Debugging: check if bot picked unknown card
            house = self.house_map.get(bot_pick_result, "Unknown")
            if house == "Unknown":
                print(f"[DEBUG] Bot {i} picked unknown card: '{bot_pick_result}' (not found in cards.json)")
            
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
            house = self.house_map.get(card, 'Unknown')
            house_grouped.setdefault(house, []).append(card)

        for house, cards in house_grouped.items():
            label = tk.Label(self.picks_frame, text=f"[{house}]", font=("Arial", 12, "bold"))
            label.pack()
            row_frame = tk.Frame(self.picks_frame)
            row_frame.pack(anchor='w', fill='x')
            max_per_row = 4
            for i in range(0, len(cards), max_per_row):
                row = tk.Frame(row_frame)
                row.pack(anchor='w')
                for c in cards[i:i+max_per_row]:
                    sanitized_name = c.replace(" ", "_").replace("'", "").replace(":", "")
                    image_path = os.path.join(CARD_IMAGE_PATH, house, f"{sanitized_name}.png")
                    try:
                        img = Image.open(image_path).resize((60, 84))
                        photo = ImageTk.PhotoImage(img)
                    except:
                        photo = ImageTk.PhotoImage(Image.new('RGB', (60, 84), color='gray'))
                    lbl = tk.Label(row, image=photo)
                    lbl.image = photo
                    lbl.pack(side=tk.LEFT, padx=2)
                    self.pick_images.append(photo)

    def finish_draft(self):
        self.update_drafted()

        # If the window is already open, bring it to front
        if self.end_window is not None and self.end_window.winfo_exists():
            self.end_window.lift()
            self.end_window.attributes('-topmost', True)
            self.end_window.attributes('-topmost', False)
            return
        
        from uuid import uuid4

        with open("bot_picks_log.json", "w", encoding="utf-8") as f:
            json.dump(get_bot_logs(), f, indent=2, ensure_ascii=False)

        def export_json():
            if self.exported:
                return

            uid = uuid4().hex[:8]
            filename = f"draft_results_{uid}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({
                    f"Player {i+1}": [{"id": idx + 1, "card": card} for idx, card in enumerate(picks)]
                    for i, picks in enumerate(self.players)
                }, f, indent=2, ensure_ascii=False)

            self.exported = True

            # Close the old end window
            if self.end_window and self.end_window.winfo_exists():
                self.end_window.destroy()
                self.end_window = None

            # Show confirmation message
            messagebox.showinfo("Exported", f"Draft results saved to {filename}")

            # Automatically reopen the "Draft Complete" window with export disabled
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
    app = DraftUI(root)
    root.mainloop()
