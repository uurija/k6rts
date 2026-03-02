import json
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict, List

APP_TITLE = "Lauateeninduse Süsteem"
DEFAULT_LAYOUT_FILE = "table_layout.json"
CODES_FILE = "access_codes.json"
SUPER_CODE = "0000"
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

    def has_unpaid(self) -> bool:
        return any(self.guest_total(guest) > 0 for guest in self.guests)

    def has_orders(self) -> bool:
        return any(len(items) > 0 for items in self.guests.values())

    def mark_guest_paid(self, guest_id: str):
        if guest_id in self.guests:
            self.guests[guest_id] = []


class RestaurantServiceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x720")

        self.layout_file = Path(DEFAULT_LAYOUT_FILE)
        self.codes_file = Path(CODES_FILE)

        self.codes: List[str] = []
        self.current_code: str | None = None
        self.table_layout: Dict[int, Dict] = {}
        self.table_data: Dict[int, TableData] = {}
        self.selected_table: int | None = None
        self.pending_table: Dict | None = None
        self.order_window: tk.Toplevel | None = None

        self._load_codes()
        self._build_ui()
        self.load_layout(self.layout_file)
        self.after(50, self.require_authentication)

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)

        self.user_label = ttk.Label(top, text="Kasutaja: -", font=("Segoe UI", 10, "bold"))
        self.user_label.pack(side="left", padx=6)

        self.add_table_btn = ttk.Button(top, text="Lisa laud", command=self.add_table_dialog)
        self.add_table_btn.pack(side="left", padx=4)

        self.manage_codes_btn = ttk.Button(top, text="Lisa pääsukood", command=self.add_code_dialog)
        self.manage_codes_btn.pack(side="left", padx=4)

        ttk.Button(top, text="Salvesta kaart", command=self.save_layout_dialog).pack(side="left", padx=4)
        ttk.Button(top, text="Laadi kaart", command=self.load_layout_dialog).pack(side="left", padx=4)
        ttk.Button(top, text="Logi välja", command=self.logout).pack(side="right", padx=4)

        self.map_canvas = tk.Canvas(self, bg="#f6f8fa")
        self.map_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.map_canvas.bind("<Button-1>", self._on_canvas_click)

        self.map_hint_label = ttk.Label(self, text="")
        self.map_hint_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _load_codes(self):
        if self.codes_file.exists():
            try:
                raw = json.loads(self.codes_file.read_text(encoding="utf-8"))
                loaded = raw.get("codes", [])
                valid = [code for code in loaded if isinstance(code, str) and code.isdigit() and len(code) == 4]
                self.codes = sorted(set(valid + [SUPER_CODE]))
                return
            except Exception:
                pass
        self.codes = [SUPER_CODE]
        self._save_codes()

    def _save_codes(self):
        self.codes_file.write_text(json.dumps({"codes": sorted(set(self.codes))}, indent=2), encoding="utf-8")

    def _is_super(self) -> bool:
        return self.current_code == SUPER_CODE

    def _update_role_controls(self):
        if self._is_super():
            self.add_table_btn.state(["!disabled"])
            self.manage_codes_btn.state(["!disabled"])
        else:
            self.add_table_btn.state(["disabled"])
            self.manage_codes_btn.state(["disabled"])
        who = self.current_code if self.current_code else "-"
        suffix = " (SUPER)" if self._is_super() else ""
        self.user_label.config(text=f"Kasutaja: {who}{suffix}")

    def _front_dialog(self, dialog: tk.Toplevel, parent: tk.Misc | None = None):
        owner = parent if parent is not None else self
        dialog.transient(owner)
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

    def require_authentication(self):
        while True:
            code = simpledialog.askstring("Autentimine", "Sisesta 4-kohaline pääsukood:", parent=self)
            if code is None:
                self.destroy()
                return
            code = code.strip()
            if code in self.codes:
                self.current_code = code
                self._update_role_controls()
                self.redraw_map()
                return
            messagebox.showerror(APP_TITLE, "Vale kood.", parent=self)

    def logout(self):
        self.current_code = None
        self.selected_table = None
        if self.order_window and self.order_window.winfo_exists():
            self.order_window.destroy()
        self._update_role_controls()
        self.require_authentication()

    def add_code_dialog(self):
        if not self._is_super():
            messagebox.showwarning(APP_TITLE, "Ainult SUPER saab koode lisada.", parent=self)
            return
        code = simpledialog.askstring("Uus kood", "Sisesta uus 4-kohaline kood:", parent=self)
        if not code:
            return
        code = code.strip()
        if len(code) != 4 or not code.isdigit():
            messagebox.showerror(APP_TITLE, "Kood peab olema 4-kohaline number.", parent=self)
            return
        self.codes.append(code)
        self._save_codes()
        messagebox.showinfo(APP_TITLE, f"Kood {code} lisatud.", parent=self)

    def add_table_dialog(self):
        if not self._is_super():
            messagebox.showwarning(APP_TITLE, "Laua lisamine on ainult SUPER kasutajale.", parent=self)
            return

        number = simpledialog.askinteger("Laua number", "Sisesta laua number:", minvalue=1, parent=self)
        if not number:
            return
        up = simpledialog.askinteger("Ülemine külg", "Mitu inimest istub üleval küljel?", minvalue=0, parent=self)
        right = simpledialog.askinteger("Parem külg", "Mitu inimest istub paremal küljel?", minvalue=0, parent=self)
        down = simpledialog.askinteger("Alumine külg", "Mitu inimest istub all küljel?", minvalue=0, parent=self)
        left = simpledialog.askinteger("Vasak külg", "Mitu inimest istub vasakul küljel?", minvalue=0, parent=self)
        if None in (up, right, down, left):
            return
        if up + right + down + left == 0:
            messagebox.showwarning(APP_TITLE, "Laual peab olema vähemalt 1 istekoht.", parent=self)
            return

        self.pending_table = {"number": number, "sides": {"up": up, "right": right, "down": down, "left": left}}
        self.table_data.setdefault(number, TableData(number))
        self.map_hint_label.config(text=f"Klõpsa kaardil laua {number} keskpunkti asukohta.")

    def _table_size(self, sides: Dict[str, int]) -> tuple[int, int]:
        width = max(MIN_TABLE_SIDE, max(1, max(sides["up"], sides["down"])) * BASE_UNIT)
        height = max(MIN_TABLE_SIDE, max(1, max(sides["left"], sides["right"])) * BASE_UNIT)
        return width, height

    def _table_bounds(self, entry: Dict) -> tuple[int, int, int, int]:
        cx, cy = entry["center"]["x"], entry["center"]["y"]
        w, h = self._table_size(entry["sides"])
        return cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2

    def _seat_points(self, entry: Dict) -> List[tuple[float, float, int]]:
        left, top, right, bottom = self._table_bounds(entry)
        sides = entry["sides"]
        points: List[tuple[float, float, int]] = []
        seat_number = 1

        def spread(start: float, end: float, count: int):
            if count <= 0:
                return []
            step = (end - start) / (count + 1)
            return [start + step * (i + 1) for i in range(count)]

        for x in spread(left, right, sides["up"]):
            points.append((x, top - SEAT_OFFSET, seat_number))
            seat_number += 1
        for y in spread(top, bottom, sides["right"]):
            points.append((right + SEAT_OFFSET, y, seat_number))
            seat_number += 1
        for x in reversed(spread(left, right, sides["down"])):
            points.append((x, bottom + SEAT_OFFSET, seat_number))
            seat_number += 1
        for y in reversed(spread(top, bottom, sides["left"])):
            points.append((left - SEAT_OFFSET, y, seat_number))
            seat_number += 1
        return points

    def _table_owner(self, table_num: int) -> str | None:
        return self.table_layout.get(table_num, {}).get("owner")

    def _is_free(self, table_num: int) -> bool:
        table = self.table_data.setdefault(table_num, TableData(table_num))
        return not table.has_orders()

    def _table_accessible(self, table_num: int) -> bool:
        if self._is_super():
            return True
        if self._is_free(table_num):
            return True
        return self._table_owner(table_num) == self.current_code

    def _table_color(self, table_num: int) -> str:
        if self.selected_table == table_num:
            return "#0b3d91"
        if self._is_free(table_num):
            return "#2ea043"  # green
        if self._table_owner(table_num) == self.current_code:
            return "#f2cc60"  # yellow
        return "#d73a49"  # red

    def _claim_if_needed(self, table_num: int):
        if self._is_super():
            return
        table = self.table_data.setdefault(table_num, TableData(table_num))
        if table.has_orders() and self._table_owner(table_num) is None:
            self.table_layout[table_num]["owner"] = self.current_code

    def _release_if_free(self, table_num: int):
        if self._is_free(table_num):
            self.table_layout[table_num]["owner"] = None

    def redraw_map(self):
        self.map_canvas.delete("all")
        for table_num, entry in sorted(self.table_layout.items()):
            self._release_if_free(table_num)
            left, top, right, bottom = self._table_bounds(entry)
            fill = self._table_color(table_num)
            self.map_canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="#0b3d91", width=2)
            self.map_canvas.create_text((left + right) // 2, (top + bottom) // 2, text=f"Laud {table_num}", fill="white", font=("Segoe UI", 10, "bold"))
            for x, y, n in self._seat_points(entry):
                self.map_canvas.create_oval(x - SEAT_RADIUS, y - SEAT_RADIUS, x + SEAT_RADIUS, y + SEAT_RADIUS, fill="#ffd166", outline="#8a5b00")
                self.map_canvas.create_text(x, y, text=str(n), font=("Segoe UI", 9, "bold"))

    def _on_canvas_click(self, event):
        if self.pending_table is not None:
            n = self.pending_table["number"]
            self.table_layout[n] = {"center": {"x": event.x, "y": event.y}, "sides": self.pending_table["sides"], "owner": None}
            self.pending_table = None
            self.selected_table = n
            self.map_hint_label.config(text="")
            self.redraw_map()
            return

        for table_num, entry in self.table_layout.items():
            left, top, right, bottom = self._table_bounds(entry)
            if left <= event.x <= right and top <= event.y <= bottom:
                if not self._table_accessible(table_num):
                    messagebox.showwarning(APP_TITLE, "See laud on hõivatud teise koodi poolt.", parent=self)
                    return
                self.selected_table = table_num
                self.redraw_map()
                self.open_order_window()
                return

    def _current_table(self) -> TableData | None:
        if self.selected_table is None:
            messagebox.showwarning(APP_TITLE, "Vali laud kaardilt.", parent=self)
            return None
        return self.table_data.setdefault(self.selected_table, TableData(self.selected_table))

    def open_order_window(self):
        table = self._current_table()
        if not table:
            return
        table_num = self.selected_table
        assert table_num is not None
        if not self._table_accessible(table_num):
            messagebox.showwarning(APP_TITLE, "Lauale puudub ligipääs.", parent=self)
            return

        if self.order_window and self.order_window.winfo_exists():
            self.order_window.destroy()

        dlg = tk.Toplevel(self)
        dlg.title(f"Tellimused - Laud {table_num}")
        dlg.geometry("700x620")
        self._front_dialog(dlg)
        self.order_window = dlg

        ttk.Label(dlg, text=f"Laud {table_num}", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        controls = ttk.Frame(dlg)
        controls.pack(fill="x", padx=12, pady=4)
        ttk.Button(controls, text="Lisa külaline", command=lambda: self.add_guest_dialog(parent=dlg)).pack(side="left", padx=3)
        ttk.Button(controls, text="Lisa tellimus", command=lambda: self.add_order_dialog(parent=dlg)).pack(side="left", padx=3)
        ttk.Button(controls, text="Maksa külaline", command=lambda: self.pay_guest_dialog(parent=dlg)).pack(side="left", padx=3)

        columns = ("guest", "item", "qty", "unit", "total")
        tree = ttk.Treeview(dlg, columns=columns, show="headings", height=18)
        for col, title, width in [("guest", "Külaline", 120), ("item", "Toode", 200), ("qty", "Kogus", 70), ("unit", "Ühik", 90), ("total", "Summa", 90)]:
            tree.heading(col, text=title)
            tree.column(col, width=width)
        tree.pack(fill="both", expand=True, padx=12, pady=6)

        total_label = ttk.Label(dlg, text="Laua kogusumma: 0.00 €", font=("Segoe UI", 11, "bold"))
        total_label.pack(anchor="w", padx=12)
        output = tk.Text(dlg, height=7)
        output.pack(fill="x", padx=12, pady=(4, 10))

        self._order_tree = tree
        self._order_total_label = total_label
        self._order_output = output
        self._refresh_order_widgets(tree, total_label)

        def close_order_window():
            dlg.destroy()
            self.redraw_map()

        dlg.protocol("WM_DELETE_WINDOW", close_order_window)

    def _refresh_order_widgets(self, tree: ttk.Treeview, total_label: ttk.Label):
        table = self._current_table()
        if not table:
            return
        if self.selected_table is not None:
            self._claim_if_needed(self.selected_table)
            self._release_if_free(self.selected_table)
        for row in tree.get_children():
            tree.delete(row)
        for guest, items in table.guests.items():
            for order in items:
                tree.insert("", "end", values=(guest, order.name, order.qty, f"{order.unit_price:.2f}", f"{order.total:.2f}"))
        total_label.config(text=f"Laua kogusumma: {table.total():.2f} €")
        self.redraw_map()

    def add_guest_dialog(self, parent: tk.Misc | None = None):
        table = self._current_table()
        if not table:
            return
        guest = simpledialog.askstring("Külaline", "Sisesta külalise ID (nt K1):", parent=parent or self)
        if guest:
            table.add_guest(guest.strip())
            if self.order_window and self.order_window.winfo_exists():
                self._refresh_order_widgets(self._order_tree, self._order_total_label)

    def add_order_dialog(self, parent: tk.Misc | None = None):
        table = self._current_table()
        if not table:
            return
        if not table.guests:
            messagebox.showinfo(APP_TITLE, "Lisa enne külaline.", parent=parent or self)
            return

        dlg = tk.Toplevel(parent or self)
        dlg.title("Lisa tellimus")
        dlg.geometry("360x240")
        self._front_dialog(dlg, parent=parent)

        ttk.Label(dlg, text="Külaline").pack(anchor="w", padx=12, pady=(12, 0))
        guest_var = tk.StringVar(value=next(iter(table.guests.keys())))
        guest_combo = ttk.Combobox(dlg, textvariable=guest_var, values=list(table.guests.keys()), state="readonly")
        guest_combo.pack(fill="x", padx=12)

        ttk.Label(dlg, text="Toode").pack(anchor="w", padx=12, pady=(10, 0))
        item_var = tk.StringVar()
        item_entry = ttk.Entry(dlg, textvariable=item_var)
        item_entry.pack(fill="x", padx=12)

        ttk.Label(dlg, text="Kogus").pack(anchor="w", padx=12, pady=(10, 0))
        qty_var = tk.IntVar(value=1)
        ttk.Spinbox(dlg, from_=1, to=99, textvariable=qty_var).pack(fill="x", padx=12)

        ttk.Label(dlg, text="Ühiku hind (€)").pack(anchor="w", padx=12, pady=(10, 0))
        price_var = tk.DoubleVar(value=0.0)
        ttk.Entry(dlg, textvariable=price_var).pack(fill="x", padx=12)

        item_entry.focus_set()

        def save():
            try:
                new_item = OrderItem(guest_id=guest_var.get(), name=item_var.get().strip(), qty=int(qty_var.get()), unit_price=float(price_var.get()))
            except ValueError:
                messagebox.showerror(APP_TITLE, "Kontrolli sisendit.", parent=dlg)
                return
            if not new_item.name:
                messagebox.showerror(APP_TITLE, "Toode ei tohi olla tühi.", parent=dlg)
                return
            if self.selected_table is not None and not self._table_accessible(self.selected_table):
                messagebox.showwarning(APP_TITLE, "Sellele lauale ei ole õigust tellimust lisada.", parent=dlg)
                return
            table.add_order(new_item)
            if self.selected_table is not None:
                self._claim_if_needed(self.selected_table)
            dlg.destroy()
            if self.order_window and self.order_window.winfo_exists():
                self._refresh_order_widgets(self._order_tree, self._order_total_label)

        ttk.Button(dlg, text="Salvesta", command=save).pack(pady=12)

    def _build_guest_receipt(self, table: TableData, guest: str) -> str:
        lines = [f"TŠEKK / Laud {table.table_number}", f"Külaline: {guest}", "-------------------------"]
        for item in table.guests.get(guest, []):
            lines.append(f"{item.qty}x {item.name:<12} {item.total:>6.2f} €")
        lines.append("-------------------------")
        lines.append(f"Kokku: {table.guest_total(guest):.2f} €")
        return "\n".join(lines)

    def pay_guest_dialog(self, parent: tk.Misc | None = None):
        table = self._current_table()
        if not table:
            return
        if self.selected_table is not None and not self._table_accessible(self.selected_table):
            messagebox.showwarning(APP_TITLE, "Sellele lauale puudub ligipääs.", parent=parent or self)
            return

        payable = [g for g in table.guests if table.guest_total(g) > 0]
        if not payable:
            messagebox.showinfo(APP_TITLE, "Tasumata külalisi pole.", parent=parent or self)
            return

        dlg = tk.Toplevel(parent or self)
        dlg.title("Külalise makse")
        dlg.geometry("430x470")
        self._front_dialog(dlg, parent=parent)

        guest_var = tk.StringVar(value=payable[0])
        method_var = tk.StringVar(value="cash")
        cash_var = tk.StringVar(value="")

        ttk.Label(dlg, text="Vali külaline:").pack(anchor="w", padx=12, pady=(12, 0))
        ttk.Combobox(dlg, textvariable=guest_var, values=payable, state="readonly").pack(fill="x", padx=12)
        ttk.Label(dlg, text="Tšekk:").pack(anchor="w", padx=12, pady=(10, 0))
        receipt = tk.Text(dlg, height=12)
        receipt.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        def refresh_receipt(*_):
            receipt.config(state="normal")
            receipt.delete("1.0", tk.END)
            receipt.insert("1.0", self._build_guest_receipt(table, guest_var.get()))
            receipt.config(state="disabled")

        frame = ttk.LabelFrame(dlg, text="Maksmise viis")
        frame.pack(fill="x", padx=12, pady=4)
        ttk.Radiobutton(frame, text="Sularaha", variable=method_var, value="cash").pack(anchor="w", padx=8, pady=3)
        ttk.Radiobutton(frame, text="Kaart", variable=method_var, value="card").pack(anchor="w", padx=8, pady=3)

        cash_frame = ttk.Frame(dlg)
        cash_frame.pack(fill="x", padx=12, pady=(2, 8))
        ttk.Label(cash_frame, text="Antud sularaha (€):").pack(side="left")
        cash_entry = ttk.Entry(cash_frame, textvariable=cash_var, width=12)
        cash_entry.pack(side="left", padx=6)

        def on_method(*_):
            if method_var.get() == "cash":
                cash_frame.pack(fill="x", padx=12, pady=(2, 8))
                cash_entry.focus_set()
            else:
                cash_frame.pack_forget()

        def finish():
            guest = guest_var.get()
            total = table.guest_total(guest)
            receipt_text = self._build_guest_receipt(table, guest)
            if method_var.get() == "cash":
                try:
                    paid = float(cash_var.get())
                except ValueError:
                    messagebox.showerror(APP_TITLE, "Sisesta korrektne sularaha summa.", parent=dlg)
                    return
                if paid < total:
                    messagebox.showerror(APP_TITLE, "Sularaha summa on väiksem kui arve.", parent=dlg)
                    return
                change = paid - total
                table.mark_guest_paid(guest)
                self._order_output.delete("1.0", tk.END)
                self._order_output.insert("1.0", f"{receipt_text}\n\nMakse: sularaha\nSaadud: {paid:.2f} €\nTagastus: {change:.2f} €")
                dlg.destroy()
            else:
                card = tk.Toplevel(dlg)
                card.title("Kaardimakse")
                card.geometry("280x140")
                self._front_dialog(card, parent=dlg)
                ttk.Label(card, text="Sisesta kaart...", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))

                def done():
                    table.mark_guest_paid(guest)
                    self._order_output.delete("1.0", tk.END)
                    self._order_output.insert("1.0", f"{receipt_text}\n\nMakse: kaart\nStaatus: Tasutud")
                    card.destroy()
                    dlg.destroy()
                    if self.order_window and self.order_window.winfo_exists():
                        self._refresh_order_widgets(self._order_tree, self._order_total_label)

                ttk.Button(card, text="Makse tehtud", command=done).pack(pady=6)
                return

            if self.order_window and self.order_window.winfo_exists():
                self._refresh_order_widgets(self._order_tree, self._order_total_label)

        ttk.Button(dlg, text="Kinnita makse", command=finish).pack(pady=(4, 12))

        guest_var.trace_add("write", refresh_receipt)
        method_var.trace_add("write", on_method)
        on_method()
        refresh_receipt()

    def save_layout(self):
        self.layout_file.write_text(json.dumps({"tables": self.table_layout}, indent=2), encoding="utf-8")

    def save_layout_dialog(self):
        file = filedialog.asksaveasfilename(title="Salvesta kaardi fail", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not file:
            return
        self.layout_file = Path(file)
        self.save_layout()
        messagebox.showinfo(APP_TITLE, "Kaart salvestatud.", parent=self)

    def load_layout(self, path: Path):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                raw = data.get("tables", {})
                self.table_layout = {int(k): v for k, v in raw.items()}
            except Exception as exc:
                messagebox.showwarning(APP_TITLE, f"Kaardi laadimine ebaõnnestus: {exc}", parent=self)
                self.table_layout = {}
        else:
            self.table_layout = {
                1: {"center": {"x": 100, "y": 100}, "sides": {"up": 2, "right": 2, "down": 2, "left": 2}, "owner": None},
                2: {"center": {"x": 280, "y": 140}, "sides": {"up": 1, "right": 3, "down": 1, "left": 3}, "owner": None},
            }
        for number in self.table_layout:
            self.table_data.setdefault(number, TableData(number))
            self.table_layout[number].setdefault("owner", None)
        self.redraw_map()

    def load_layout_dialog(self):
        file = filedialog.askopenfilename(title="Vali kaardi fail", filetypes=[("JSON", "*.json")])
        if not file:
            return
        self.layout_file = Path(file)
        self.load_layout(self.layout_file)
        messagebox.showinfo(APP_TITLE, "Kaart laetud.", parent=self)


if __name__ == "__main__":
    app = RestaurantServiceApp()
    app.mainloop()
