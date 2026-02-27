import json
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict, List

APP_TITLE = "Lauateeninduse Süsteem"
DEFAULT_LAYOUT_FILE = "table_layout.json"
TABLE_DIAMETER = 70


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
        self.table_positions: Dict[int, Dict[str, int]] = {}
        self.table_data: Dict[int, TableData] = {}
        self.selected_table: int | None = None
        self.pending_table_number: int | None = None

        self._build_ui()
        self.load_layout(self.layout_file)

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Button(top, text="Lisa laud (klõps kaardil)", command=self.add_table_dialog).pack(side="left", padx=4)
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
        table_number = simpledialog.askinteger("Laua number", "Sisesta laua number:", minvalue=1)
        if not table_number:
            return
        self.pending_table_number = table_number
        self.table_data.setdefault(table_number, TableData(table_number))
        self.map_hint_label.config(text=f"Klõpsa kaardil, kuhu soovid paigutada laua {table_number} keskpunkti.")

    def redraw_map(self):
        self.map_canvas.delete("all")
        for table_num, pos in sorted(self.table_positions.items()):
            x, y = pos["x"], pos["y"]
            fill = "#1f6feb" if table_num == self.selected_table else "#58a6ff"
            self.map_canvas.create_oval(x, y, x + TABLE_DIAMETER, y + TABLE_DIAMETER, fill=fill, outline="")
            self.map_canvas.create_text(
                x + TABLE_DIAMETER // 2,
                y + TABLE_DIAMETER // 2,
                text=f"Laud {table_num}",
                fill="white",
                font=("Segoe UI", 10, "bold"),
            )

    def _on_canvas_click(self, event):
        if self.pending_table_number is not None:
            left_x = max(0, event.x - TABLE_DIAMETER // 2)
            left_y = max(0, event.y - TABLE_DIAMETER // 2)
            self.table_positions[self.pending_table_number] = {"x": left_x, "y": left_y}
            self.selected_table = self.pending_table_number
            self.pending_table_number = None
            self.table_label.config(text=f"Valitud laud: {self.selected_table}")
            self.map_hint_label.config(text="")
            self.redraw_map()
            self.refresh_orders()
            return

        for table_num, pos in self.table_positions.items():
            x, y = pos["x"], pos["y"]
            if x <= event.x <= x + TABLE_DIAMETER and y <= event.y <= y + TABLE_DIAMETER:
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
        guest_box = ttk.Combobox(dlg, textvariable=guest_var, values=payable_guests, state="readonly")
        guest_box.pack(fill="x", padx=12)

        ttk.Label(dlg, text="Tšekk:").pack(anchor="w", padx=12, pady=(10, 0))
        receipt = tk.Text(dlg, height=12)
        receipt.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        def refresh_receipt(*_):
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
        data = {"tables": self.table_positions}
        self.layout_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

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
                raw_tables = data.get("tables", {})
                self.table_positions = {int(k): v for k, v in raw_tables.items()}
                for number in self.table_positions:
                    self.table_data.setdefault(number, TableData(number))
            except Exception as exc:
                messagebox.showwarning(APP_TITLE, f"Kaardi laadimine ebaõnnestus: {exc}")
                self.table_positions = {}
        else:
            self.table_positions = {1: {"x": 40, "y": 40}, 2: {"x": 170, "y": 40}, 3: {"x": 300, "y": 40}}
            for number in self.table_positions:
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
