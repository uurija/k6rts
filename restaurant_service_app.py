import json
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict, List

APP_TITLE = "Lauateeninduse Süsteem"
DEFAULT_LAYOUT_FILE = "table_layout.json"
BASE_UNIT = 36
MIN_TABLE_SIDE = 80
SEAT_RADIUS = 12
SEAT_OFFSET = 24


@dataclass
class OrderItem:
    guest_id: str
    name: str
    qty: int
    unit_price: float

    @property
    def total(self) -> float:
        return self.qty * self.unit_price


class TableData:
    def __init__(self, table_number: int):
        self.table_number = table_number
        self.guests: Dict[str, List[OrderItem]] = {}

    def add_guest(self, guest_id: str):
        if guest_id not in self.guests:
            self.guests[guest_id] = []

    def add_order(self, item: OrderItem):
        self.add_guest(item.guest_id)
        self.guests[item.guest_id].append(item)

    def total(self) -> float:
        return sum(item.total for items in self.guests.values() for item in items)

    def guest_total(self, guest_id: str) -> float:
        return round(sum(item.total for item in self.guests.get(guest_id, [])), 2)

    def totals_by_guest(self) -> Dict[str, float]:
        return {guest: self.guest_total(guest) for guest in self.guests}

    def mark_guest_paid(self, guest_id: str):
        if guest_id in self.guests:
            self.guests[guest_id] = []


class RestaurantServiceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x720")

        self.layout_file = Path(DEFAULT_LAYOUT_FILE)
        self.table_layout: Dict[int, Dict] = {}
        self.table_data: Dict[int, TableData] = {}
        self.selected_table: int | None = None
        self.pending_table: Dict | None = None

        self._build_ui()
        self.load_layout(self.layout_file)

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Button(top, text="Lisa laud (ristkülik)", command=self.add_table_dialog).pack(side="left", padx=4)
        ttk.Button(top, text="Salvesta kaart", command=self.save_layout_dialog).pack(side="left", padx=4)
        ttk.Button(top, text="Laadi kaart", command=self.load_layout_dialog).pack(side="left", padx=4)

        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=5)

        self.map_canvas = tk.Canvas(left, bg="#f6f8fa", width=500, height=650)
        self.map_canvas.pack(fill="both", expand=True)
        self.map_canvas.bind("<Button-1>", self._on_canvas_click)

        self.map_hint_label = ttk.Label(left, text="")
        self.map_hint_label.pack(anchor="w", pady=(4, 0))

        self.table_label = ttk.Label(right, text="Vali laud kaardilt", font=("Segoe UI", 14, "bold"))
        self.table_label.pack(anchor="w")

        controls = ttk.Frame(right)
        controls.pack(fill="x", pady=6)
        ttk.Button(controls, text="Lisa külaline", command=self.add_guest_dialog).pack(side="left", padx=3)
        ttk.Button(controls, text="Lisa tellimus", command=self.add_order_dialog).pack(side="left", padx=3)
        ttk.Button(controls, text="Maksa külaline", command=self.pay_guest_dialog).pack(side="left", padx=3)

        self.orders_tree = ttk.Treeview(right, columns=("guest", "item", "qty", "unit", "total"), show="headings", height=20)
        for col, title, width in [
            ("guest", "Külaline", 120),
            ("item", "Toode", 180),
            ("qty", "Kogus", 80),
            ("unit", "Ühiku hind", 100),
            ("total", "Summa", 100),
        ]:
            self.orders_tree.heading(col, text=title)
            self.orders_tree.column(col, width=width)
        self.orders_tree.pack(fill="both", expand=True)

        footer = ttk.Frame(right)
        footer.pack(fill="x", pady=8)

        self.total_label = ttk.Label(footer, text="Laua kogusumma: 0.00 €", font=("Segoe UI", 11, "bold"))
        self.total_label.pack(anchor="w")

        self.split_text = tk.Text(footer, height=7)
        self.split_text.pack(fill="x", pady=4)

        split_buttons = ttk.Frame(footer)
        split_buttons.pack(fill="x")
        ttk.Button(split_buttons, text="Näita jagatud arvet", command=self.show_split_bill).pack(side="left", padx=3)
        ttk.Button(split_buttons, text="Näita ühist arvet", command=self.show_shared_bill).pack(side="left", padx=3)

    def add_table_dialog(self):
        number = simpledialog.askinteger("Laua number", "Sisesta laua number:", minvalue=1)
        if not number:
            return

        up = simpledialog.askinteger("Ülemine külg", "Mitu inimest istub üleval küljel?", minvalue=0)
        right = simpledialog.askinteger("Parem külg", "Mitu inimest istub paremal küljel?", minvalue=0)
        down = simpledialog.askinteger("Alumine külg", "Mitu inimest istub all küljel?", minvalue=0)
        left = simpledialog.askinteger("Vasak külg", "Mitu inimest istub vasakul küljel?", minvalue=0)
        if None in (up, right, down, left):
            return
        if up + right + down + left == 0:
            messagebox.showwarning(APP_TITLE, "Laual peab olema vähemalt 1 istekoht.")
            return

        self.pending_table = {
            "number": number,
            "sides": {"up": up, "right": right, "down": down, "left": left},
        }
        self.table_data.setdefault(number, TableData(number))
        self.map_hint_label.config(text=f"Klõpsa kaardil laua {number} keskpunkti asukohta.")

    def _table_size(self, sides: Dict[str, int]) -> tuple[int, int]:
        width_units = max(1, max(sides["up"], sides["down"]))
        height_units = max(1, max(sides["left"], sides["right"]))
        width = max(MIN_TABLE_SIDE, width_units * BASE_UNIT)
        height = max(MIN_TABLE_SIDE, height_units * BASE_UNIT)
        return width, height

    def _table_bounds(self, table_entry: Dict) -> tuple[int, int, int, int]:
        center_x = table_entry["center"]["x"]
        center_y = table_entry["center"]["y"]
        width, height = self._table_size(table_entry["sides"])
        half_w = width // 2
        half_h = height // 2
        return center_x - half_w, center_y - half_h, center_x + half_w, center_y + half_h

    def _seat_points(self, table_entry: Dict) -> List[tuple[float, float, int]]:
        left, top, right, bottom = self._table_bounds(table_entry)
        sides = table_entry["sides"]
        points: List[tuple[float, float, int]] = []
        number = 1

        def spread(start: float, end: float, count: int) -> List[float]:
            if count <= 0:
                return []
            step = (end - start) / (count + 1)
            return [start + step * (idx + 1) for idx in range(count)]

        # Clockwise numbering from top-left direction.
        for x in spread(left, right, sides["up"]):
            points.append((x, top - SEAT_OFFSET, number))
            number += 1
        for y in spread(top, bottom, sides["right"]):
            points.append((right + SEAT_OFFSET, y, number))
            number += 1
        for x in reversed(spread(left, right, sides["down"])):
            points.append((x, bottom + SEAT_OFFSET, number))
            number += 1
        for y in reversed(spread(top, bottom, sides["left"])):
            points.append((left - SEAT_OFFSET, y, number))
            number += 1

        return points

    def redraw_map(self):
        self.map_canvas.delete("all")
        for table_num, table_entry in sorted(self.table_layout.items()):
            left, top, right, bottom = self._table_bounds(table_entry)
            fill = "#1f6feb" if table_num == self.selected_table else "#58a6ff"
            self.map_canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="#0b3d91", width=2)
            self.map_canvas.create_text((left + right) // 2, (top + bottom) // 2, text=f"Laud {table_num}", fill="white", font=("Segoe UI", 10, "bold"))

            for seat_x, seat_y, seat_num in self._seat_points(table_entry):
                self.map_canvas.create_oval(
                    seat_x - SEAT_RADIUS,
                    seat_y - SEAT_RADIUS,
                    seat_x + SEAT_RADIUS,
                    seat_y + SEAT_RADIUS,
                    fill="#ffd166",
                    outline="#8a5b00",
                )
                self.map_canvas.create_text(seat_x, seat_y, text=str(seat_num), font=("Segoe UI", 9, "bold"))

    def _on_canvas_click(self, event):
        if self.pending_table is not None:
            number = self.pending_table["number"]
            self.table_layout[number] = {
                "center": {"x": event.x, "y": event.y},
                "sides": self.pending_table["sides"],
            }
            self.selected_table = number
            self.pending_table = None
            self.table_label.config(text=f"Valitud laud: {number}")
            self.map_hint_label.config(text="")
            self.redraw_map()
            self.refresh_orders()
            return

        for table_num, table_entry in self.table_layout.items():
            left, top, right, bottom = self._table_bounds(table_entry)
            if left <= event.x <= right and top <= event.y <= bottom:
                self.selected_table = table_num
                self.table_label.config(text=f"Valitud laud: {table_num}")
                self.redraw_map()
                self.refresh_orders()
                return

    def current_table(self) -> TableData | None:
        if self.selected_table is None:
            messagebox.showwarning(APP_TITLE, "Vali enne laud kaardilt.")
            return None
        return self.table_data.setdefault(self.selected_table, TableData(self.selected_table))

    def add_guest_dialog(self):
        table = self.current_table()
        if not table:
            return
        guest = simpledialog.askstring("Külaline", "Sisesta külalise ID (nt K1, K2):")
        if guest:
            table.add_guest(guest.strip())
            self.refresh_orders()

    def add_order_dialog(self):
        table = self.current_table()
        if not table:
            return
        if not table.guests:
            messagebox.showinfo(APP_TITLE, "Lisa kõigepealt vähemalt üks külaline.")
            return

        dlg = tk.Toplevel(self)
        dlg.title("Lisa tellimus")
        dlg.geometry("360x240")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text="Külaline").pack(anchor="w", padx=12, pady=(12, 0))
        guest_var = tk.StringVar(value=next(iter(table.guests.keys())))
        ttk.Combobox(dlg, textvariable=guest_var, values=list(table.guests.keys()), state="readonly").pack(fill="x", padx=12)

        ttk.Label(dlg, text="Toode").pack(anchor="w", padx=12, pady=(10, 0))
        item_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=item_var).pack(fill="x", padx=12)

        ttk.Label(dlg, text="Kogus").pack(anchor="w", padx=12, pady=(10, 0))
        qty_var = tk.IntVar(value=1)
        ttk.Spinbox(dlg, from_=1, to=99, textvariable=qty_var).pack(fill="x", padx=12)

        ttk.Label(dlg, text="Ühiku hind (€)").pack(anchor="w", padx=12, pady=(10, 0))
        price_var = tk.DoubleVar(value=0.0)
        ttk.Entry(dlg, textvariable=price_var).pack(fill="x", padx=12)

        def save():
            name = item_var.get().strip()
            if not name:
                messagebox.showerror(APP_TITLE, "Toote nimi ei tohi olla tühi.")
                return
            try:
                item = OrderItem(
                    guest_id=guest_var.get(),
                    name=name,
                    qty=int(qty_var.get()),
                    unit_price=float(price_var.get()),
                )
            except ValueError:
                messagebox.showerror(APP_TITLE, "Kontrolli kogust ja hinda.")
                return
            table.add_order(item)
            dlg.destroy()
            self.refresh_orders()

        ttk.Button(dlg, text="Salvesta", command=save).pack(pady=14)

    def _build_guest_receipt(self, table: TableData, guest: str) -> str:
        lines = [f"TŠEKK / Laud {table.table_number}", f"Külaline: {guest}", "-------------------------"]
        for item in table.guests.get(guest, []):
            lines.append(f"{item.qty}x {item.name:<12} {item.total:>6.2f} €")
        lines.append("-------------------------")
        lines.append(f"Kokku: {table.guest_total(guest):.2f} €")
        return "\n".join(lines)

    def pay_guest_dialog(self):
        table = self.current_table()
        if not table:
            return

        payable_guests = [guest for guest in table.guests if table.guest_total(guest) > 0]
        if not payable_guests:
            messagebox.showinfo(APP_TITLE, "Sellel laual pole tasumata külalisi.")
            return

        dlg = tk.Toplevel(self)
        dlg.title("Külalise makse")
        dlg.geometry("430x470")
        dlg.transient(self)
        dlg.grab_set()

        guest_var = tk.StringVar(value=payable_guests[0])
        method_var = tk.StringVar(value="cash")
        cash_amount_var = tk.StringVar(value="")

        ttk.Label(dlg, text="Vali külaline:").pack(anchor="w", padx=12, pady=(12, 0))
        ttk.Combobox(dlg, textvariable=guest_var, values=payable_guests, state="readonly").pack(fill="x", padx=12)

        ttk.Label(dlg, text="Tšekk:").pack(anchor="w", padx=12, pady=(10, 0))
        receipt = tk.Text(dlg, height=12)
        receipt.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        def refresh_receipt(*_):
            receipt.config(state="normal")
            receipt.delete("1.0", tk.END)
            receipt.insert("1.0", self._build_guest_receipt(table, guest_var.get()))
            receipt.config(state="disabled")

        method_frame = ttk.LabelFrame(dlg, text="Maksmise viis")
        method_frame.pack(fill="x", padx=12, pady=4)
        ttk.Radiobutton(method_frame, text="Sularaha", variable=method_var, value="cash").pack(anchor="w", padx=8, pady=3)
        ttk.Radiobutton(method_frame, text="Kaart", variable=method_var, value="card").pack(anchor="w", padx=8, pady=3)

        cash_frame = ttk.Frame(dlg)
        cash_frame.pack(fill="x", padx=12, pady=(2, 8))
        ttk.Label(cash_frame, text="Antud sularaha (€):").pack(side="left")
        ttk.Entry(cash_frame, textvariable=cash_amount_var, width=12).pack(side="left", padx=6)

        def on_method_change(*_):
            if method_var.get() == "cash":
                cash_frame.pack(fill="x", padx=12, pady=(2, 8))
            else:
                cash_frame.pack_forget()

        def complete_payment():
            guest = guest_var.get()
            guest_total = table.guest_total(guest)

            if method_var.get() == "cash":
                try:
                    paid = float(cash_amount_var.get())
                except ValueError:
                    messagebox.showerror(APP_TITLE, "Sisesta korrektne sularaha summa.")
                    return
                if paid < guest_total:
                    messagebox.showerror(APP_TITLE, "Sularaha summa on väiksem kui arve.")
                    return
                change = paid - guest_total
                receipt_text = self._build_guest_receipt(table, guest)
                table.mark_guest_paid(guest)
                self.refresh_orders()
                self.split_text.delete("1.0", tk.END)
                self.split_text.insert(
                    "1.0",
                    f"{receipt_text}\n\nMakse: sularaha\nSaadud: {paid:.2f} €\nTagastus: {change:.2f} €",
                )
                dlg.destroy()
                messagebox.showinfo(APP_TITLE, f"Külaline {guest} tasus sularahas.")
                return

            card_window = tk.Toplevel(dlg)
            card_window.title("Kaardimakse")
            card_window.geometry("280x140")
            card_window.transient(dlg)
            ttk.Label(card_window, text="Sisesta kaart...", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))

            def confirm_card_payment():
                receipt_text = self._build_guest_receipt(table, guest)
                table.mark_guest_paid(guest)
                self.refresh_orders()
                self.split_text.delete("1.0", tk.END)
                self.split_text.insert("1.0", f"{receipt_text}\n\nMakse: kaart\nStaatus: Tasutud")
                card_window.destroy()
                dlg.destroy()
                messagebox.showinfo(APP_TITLE, f"Külaline {guest} tasus kaardiga.")

            ttk.Button(card_window, text="Makse tehtud", command=confirm_card_payment).pack(pady=6)

        ttk.Button(dlg, text="Kinnita makse", command=complete_payment).pack(pady=(4, 12))

        guest_var.trace_add("write", refresh_receipt)
        method_var.trace_add("write", on_method_change)
        on_method_change()
        refresh_receipt()

    def refresh_orders(self):
        for row in self.orders_tree.get_children():
            self.orders_tree.delete(row)

        table = self.current_table()
        if not table:
            return

        for guest, items in table.guests.items():
            for item in items:
                self.orders_tree.insert(
                    "",
                    "end",
                    values=(guest, item.name, item.qty, f"{item.unit_price:.2f}", f"{item.total:.2f}"),
                )

        self.total_label.config(text=f"Laua kogusumma: {table.total():.2f} €")

    def show_split_bill(self):
        table = self.current_table()
        if not table:
            return
        lines = ["Jagatud arve:"]
        for guest, total in table.totals_by_guest().items():
            lines.append(f"- {guest}: {total:.2f} €")
        lines.append(f"Kokku: {table.total():.2f} €")
        self.split_text.delete("1.0", tk.END)
        self.split_text.insert("1.0", "\n".join(lines))

    def show_shared_bill(self):
        table = self.current_table()
        if not table:
            return
        self.split_text.delete("1.0", tk.END)
        self.split_text.insert("1.0", f"Ühine arve kogu lauale: {table.total():.2f} €")

    def save_layout(self):
        self.layout_file.write_text(json.dumps({"tables": self.table_layout}, indent=2), encoding="utf-8")

    def save_layout_dialog(self):
        file = filedialog.asksaveasfilename(
            title="Salvesta kaardi fail",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not file:
            return
        self.layout_file = Path(file)
        self.save_layout()
        messagebox.showinfo(APP_TITLE, "Kaart salvestatud.")

    def load_layout(self, path: Path):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                raw = data.get("tables", {})
                self.table_layout = {int(k): v for k, v in raw.items()}
                for number in self.table_layout:
                    self.table_data.setdefault(number, TableData(number))
            except Exception as exc:
                messagebox.showwarning(APP_TITLE, f"Kaardi laadimine ebaõnnestus: {exc}")
                self.table_layout = {}
        else:
            self.table_layout = {
                1: {"center": {"x": 100, "y": 100}, "sides": {"up": 2, "right": 2, "down": 2, "left": 2}},
                2: {"center": {"x": 260, "y": 120}, "sides": {"up": 1, "right": 3, "down": 1, "left": 3}},
            }
            for number in self.table_layout:
                self.table_data.setdefault(number, TableData(number))
        self.redraw_map()

    def load_layout_dialog(self):
        file = filedialog.askopenfilename(title="Vali kaardi fail", filetypes=[("JSON", "*.json")])
        if not file:
            return
        self.layout_file = Path(file)
        self.load_layout(self.layout_file)
        messagebox.showinfo(APP_TITLE, "Kaart laetud.")


if __name__ == "__main__":
    app = RestaurantServiceApp()
    app.mainloop()
