import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import tkintermapview as tmv
from pathlib import Path

import sys
import inspect
import traceback
import types
from typing import get_args, get_origin, Union

from .loader import MapDownloader
from .db import DB, Tables

MAP_DB_PATH = Path(__file__).parent / "database" / "map.db"
LARGE_FONT = ("TkTextFont", 20)


def call_with_types(func, values: dict):
    """
    Ensure that the given values match the type hints of func
    If not raise exception otherwise call the function like func(**values)
    """
    sig = inspect.signature(func)
    type_hints = func.__annotations__

    missing = []
    for name, param in sig.parameters.items():
        if (
            param.default is inspect.Parameter.empty
            and param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
            and name not in values
        ):
            missing.append(name)

    if missing:
        raise TypeError(f"Missing required values: {', '.join(missing)}")

    coerced_values = {}
    for name, hint in type_hints.items():
        if name not in values:
            continue
        val = values[name]

        origin = get_origin(hint)
        args = get_args(hint)

        target_type = None
        if origin is types.UnionType or origin is Union or origin is None:
            non_none_types = [t for t in args if t is not type(None)]
            if non_none_types:
                target_type = non_none_types[0]
        else:
            target_type = hint

        try:
            if val == "" and type(None) in args:
                coerced_values[name] = None
            elif target_type is not None:
                coerced_values[name] = target_type(val)
            else:
                coerced_values[name] = val
        except Exception as e:
            hint_name = getattr(hint, "__name__", str(hint))
            raise ValueError(
                f"Invalid type for argument '{name}': expected {hint_name}, got {val!r}"
            ) from e

    return func(**coerced_values)


class PopupBox(ctk.CTkToplevel):
    def __init__(self, root: ctk.CTk | ctk.CTkToplevel, title: str, width: float = 0.4, height: float = 0.3):
        super().__init__(root)
        self.title(title)
        self.focus_set()
        self.transient(root)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = int(screen_width * width)
        height = int(screen_height * height)

        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.title_label = ctk.CTkLabel(self, text=title, font=LARGE_FONT)
        self.title_label.pack(fill=ctk.X)

    def run(self):
        raise NotImplementedError()


class AddPopup(PopupBox):

    def __init__(self, root, db: DB, default_port: str = Tables.PORTS):
        super().__init__(root, "Add items", 0.5, 0.45)

        self.db = db
        self.values = {}
        self.table = default_port

        self.frame = ctk.CTkScrollableFrame(self)
        self.frame.pack(fill=ctk.BOTH, expand=True)

        self.table_opt = ttk.Combobox(
            self.frame, width=100, values=Tables.as_list(), state="readonly")
        self.table_opt.pack(fill="x", padx=20, pady=10)
        self.table_opt.bind("<<ComboboxSelected>>", self.build_entries)

        self.row_entries: list[tuple[str, ctk.CTkEntry]] = []
        self.data_frame = ctk.CTkFrame(self.frame)
        self.data_frame.columnconfigure(1, weight=1)
        self.data_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.table_opt.set(Tables.rget(default_port))

        self.build_entries()

        self.submit_btr = ctk.CTkButton(
            self.frame, height=60, text="Submit", command=self.submit)
        self.submit_btr.pack(fill=ctk.BOTH)

    def build_entries(self, *_):
        for e in self.row_entries:
            e[1].destroy()
        self.row_entries.clear()

        cur_table = getattr(Tables, self.table_opt.get())
        row = self.db.get_table_data_all(cur_table)[0]
        for i, col in enumerate(list(row.keys())[1:]):
            self.__add_row(i, col)

    def submit(self, *_):
        self.values = {}
        for key, entry in self.row_entries:
            if v := entry.get():
                self.values[key] = v
        self.table = getattr(Tables, self.table_opt.get())
        self.destroy()

    def run(self):
        self.focus_set()
        self.wait_window()
        return self.table, self.values

    def __add_row(self, row: int, name: str):
        ctk.CTkLabel(self.data_frame, text=name).grid(
            row=row, column=0, padx=10)

        ptext = f"Enter {name}"
        entry = ctk.CTkEntry(self.data_frame, placeholder_text=ptext)
        entry.grid(row=row, column=1, sticky="nsew", padx=10, pady=10)
        self.row_entries.append((name, entry))


class ExceptionPopup(PopupBox):

    def __init__(self, root: ctk.CTk, title: str, message: str, width: float = 0.6, height: float = 0.4):
        super().__init__(root, title, width, height)
        self.message = ctk.CTkTextbox(self, font=LARGE_FONT)
        self.message.insert("0.0", message)
        self.message.configure(state=ctk.DISABLED)
        self.message.pack(fill=ctk.BOTH, expand=True)

        self.color_exception(title)
        self.color_etc()

    def edit(self, message: str):
        self.message.configure(state=ctk.NORMAL)
        self.message.delete("0.0", ctk.END)
        self.message.insert("0.0", message)
        self.message.configure(state=ctk.NORMAL)

    def __color_text(self, tag_name, text):
        start = "1.0"
        while True:
            start = self.message.search(text, start, stopindex=ctk.END)
            if not start:
                break
            end = f"{start}+{len(text)}c"
            self.message.tag_add(tag_name, start, end)
            start = end

    def color_exception(self, exception):
        self.message.tag_config("exception", foreground="blue")
        self.__color_text("exception", exception)

    def color_etc(self):
        self.message.tag_config("upper", foreground="red")
        self.__color_text("upper", "^")

        self.message.tag_config("qoutes", foreground="lightgreen")

        start = "1.0"
        while True:
            start = self.message.search('"', start, stopindex=ctk.END)
            if not start:
                break
            end = self.message.index(f"{start}+{1}c")
            qend = self.message.search('"', end, stopindex=ctk.END)

            if not qend:
                start = end
                continue
            qend = self.message.index(f"{qend}+{1}c")

            self.message.tag_add("qoutes", start, qend)
            start = qend

    def run(self):
        self.wait_window()


class TableView(ttk.Treeview):

    def __init__(self, root):
        super().__init__(root, padding=(10, 10), show="headings", selectmode="browse")

        self.tag_configure("odd", background="#212224")
        self.tag_configure("even", background="#2f3033")

    def delete_all(self):
        self.delete(*self.get_children())

    def add_headings(self, headings: list[str]):
        self["columns"] = headings
        for col in headings:
            self.heading(col, text=col)
            self.column(col, anchor="center", width=100)

    def add_row(self, row: list):
        self.insert("", tk.END, values=row, tags="odd" if len(
            self.get_children()) % 2 else "even")

    def select_by_id(self, id: int):
        for item_id in self.get_children():
            values = self.item(item_id, "values")
            if int(values[0]) == id:
                self.selection_set(item_id)
                self.focus(item_id)
                self.see(item_id)
                break

    def get_selected_item(self):
        return self.item(self.selection()[0], "values")


class PWSM(ctk.CTk):

    def __init__(self, db: DB):
        super().__init__()
        self.__set_styles()
        self.report_callback_exception = self.__handle_exception

        self.db = db

        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        geometry = str(width) + "x" + str(height)
        self.geometry(geometry)
        self.title("Ports and Warehouses Management System")

        self.loader = MapDownloader()
        self.loader.download_world()

        self.bind("<Control-q>", lambda *_: (self.quit(), self.destroy()))
        self.bind("<Control-Q>", lambda *_: (self.quit(), self.destroy()))

        self.base_frame = ttk.Panedwindow(self, orient="horizontal")
        self.base_frame.pack(fill="both", expand=True)

        self.__init_mapview()
        self.__init_controls()
        self.__init_table_view()

    def __set_styles(self):
        style = ttk.Style(self)
        style.theme_use('default')

        ctk.set_default_color_theme("dark-blue")
        ctk.set_appearance_mode("Dark")

        style.configure("Treeview",
                        background="#2a2d2e",
                        foreground="white",
                        rowheight=25,
                        fieldbackground="#343638",
                        borderwidth=1)
        style.map('Treeview', background=[('selected', '#22559b')])

        style.configure("Treeview.Heading",
                        background="#131314",
                        foreground="white",
                        relief="flat"
                        )
        style.map("Treeview.Heading",
                  background=[('active', '#3484F0')])

    def __handle_exception(self, except_type, value, tb):
        error_message = "".join(
            traceback.format_exception(except_type, value, tb))
        error_box = ExceptionPopup(
            self, except_type.__name__, error_message if len(sys.argv) != 1 else value)
        error_box.run()

    def __init_mapview(self):
        self.map = tmv.TkinterMapView(
            self.base_frame,
            max_zoom=19,
            use_database_only=False,
            database_path=MAP_DB_PATH.as_posix(),
            bg_color="black"
        )

        self.after(100, lambda *_: self.map.set_zoom(4))
        self.map.pack(fill="both", expand=True)
        self.base_frame.add(self.map, weight=1)

        self.map.add_right_click_menu_command(
            "Add Port", self.__map_add_port, pass_coords=True)
        self.map.add_right_click_menu_command(
            "Add Warehouse", self.__map_add_warehouse, pass_coords=True)

        self.__load_mapmarkers()

    def __init_controls(self):
        self.control_frame = ctk.CTkFrame(self.base_frame)
        self.control_frame.pack(fill="both", expand=True)
        self.base_frame.add(self.control_frame, weight=1)

        self.control_frame.rowconfigure(1, weight=1)
        self.control_frame.columnconfigure(0, weight=1)
        self.control_frame.columnconfigure(1, weight=1)
        self.control_frame.columnconfigure(2, weight=1)

        self.add_btr = ctk.CTkButton(
            self.control_frame, text="Add Data", command=self.__on_click_add_item)
        self.add_btr.grid(row=0, column=0, padx=10, sticky="ew")

        self.remove_btr = ctk.CTkButton(
            self.control_frame, text="Remove Data", command=self.__on_click_remove_item, state="disabled")
        self.remove_btr.grid(row=0, column=1, padx=10, sticky="ew")

        self.info_btr = ctk.CTkButton(
            self.control_frame, text="View Info", command=self.__on_click_view_info, state="disabled")
        self.info_btr.grid(row=0, column=2, padx=10, sticky="ew")

    def __init_table_view(self):
        self.table_frame = ctk.CTkFrame(self.control_frame)
        self.table_frame.grid(
            row=1, column=0, sticky="nsew", columnspan=3, pady=10)

        self.table_opt = ttk.Combobox(
            self.table_frame, width=100, values=Tables.as_list(), state="readonly")
        self.table_opt.set("----Select Table----")
        self.table_opt.bind("<<ComboboxSelected>>",
                            lambda *_: self.__display_table(Tables.get(self.table_opt.get())))
        self.table_opt.pack(fill="x", padx=10)

        self.table_view = TableView(self.table_frame)
        self.table_view.pack(fill="both", expand=True)
        self.table_view.bind("<<TreeviewSelect>>", self.__on_table_select)

        self.table_info = None

    def __add_item(self, table: str, values: dict | None):
        if not values:
            return

        if table == Tables.PORTS:
            call_with_types(self.db.insert_port_data, values)
        elif table == Tables.WAREHOUSES:
            call_with_types(self.db.insert_warehouse_data, values)
        elif table == Tables.ITEMS:
            call_with_types(self.db.insert_item_data, values)
        elif table == Tables.INVENTORY:
            call_with_types(self.db.insert_inventory_data, values)
        elif table == Tables.SHIPPINGS:
            call_with_types(self.db.insert_shippings_data, values)
        else:
            raise RuntimeError(f"insert into for {table} is not implemented")

        self.__display_table(table)
        self.__load_mapmarkers()

    def __on_click_add_item(self):
        self.add_popup = AddPopup(self, self.db)
        table, values = self.add_popup.run()
        self.__add_item(table, values)

    def __on_click_remove_item(self):
        values = self.table_view.get_selected_item()
        self.db.delete_row(self.current_table, int(values[0]))

        self.__display_table(self.current_table)
        self.__load_mapmarkers()

    def __on_click_view_info(self):
        if "Info" in self.current_table:
            self.__display_table(self.current_table[:-5])
            self.__on_table_select()
            return

        values = self.table_view.get_selected_item()
        id = int(values[0])

        if self.current_table == Tables.PORTS:
            rel_values = self.db.get_port_relations(id)
            info_values = self.db.get_port_info(id)
        elif self.current_table == Tables.WAREHOUSES:
            rel_values = self.db.get_warehouse_relations(id)
            info_values = self.db.get_warehouse_info(id)
        elif self.current_table == Tables.ITEMS:
            rel_values = self.db.get_item_relations(id)
            info_values = self.db.get_item_info(id)
        elif self.current_table == Tables.INVENTORY:
            rel_values = self.db.get_inventory_relations(id)
            info_values = self.db.get_inventory_info(id)
        elif self.current_table == Tables.SHIPPINGS:
            rel_values = None
            info_values = self.db.get_shipping_info(id)
        else:
            return

        if not self.table_info is None:
            self.table_info.delete_all()
        self.table_view.delete_all()

        self.table_view.add_headings(list(info_values[0].keys()))
        for data in info_values:
            self.table_view.add_row(list(data.values()))

        self.table_opt.set(Tables.rget(self.current_table) + " INFO")
        self.table_opt.selection_clear()
        self.current_table += " Info"

        if not rel_values is None:
            self.table_info = TableView(self.table_frame)
            self.table_info.pack(fill="both", expand=True)

            self.table_info.add_headings(list(rel_values[0].keys()))
            for data in rel_values:
                self.table_info.add_row(list(data.values()))

        self.__on_table_select()

    def __on_table_select(self, *_):
        self.map.delete_all_path()
        if "Info" in self.current_table:
            self.info_btr.configure(text=f"Back", state="normal")
            self.remove_btr.configure(state="disabled")

        elif self.table_view.selection():
            self.info_btr.configure(
                text=f"{self.current_table} Info", state="normal")
            self.remove_btr.configure(state="normal")

            if self.current_table in [Tables.PORTS, Tables.WAREHOUSES]:
                values = self.table_view.get_selected_item()
                self.map.set_position(float(values[2]), float(values[3]))

            if self.current_table == Tables.SHIPPINGS:
                id = self.table_view.get_selected_item()[0]
                loc_data = self.db.get_shipping_locations(int(id))
                self.map.set_path(loc_data)
        else:
            self.remove_btr.configure(state="disabled")
            self.info_btr.configure(text="View Info", state="disabled")

    def __on_click_port_mark(self, event, id):
        self.__display_table(Tables.PORTS)
        self.table_view.select_by_id(id)

    def __on_click_warehouse_mark(self, event, id):
        self.__display_table(Tables.WAREHOUSES)
        self.table_view.select_by_id(id)

    def __map_add_item(self, table, coords):
        popup = AddPopup(self, self.db, table)
        for name, entry in popup.row_entries:
            if name == "latitude":
                entry.insert(0, coords[0])
            elif name == "longitude":
                entry.insert(0, coords[1])
        table, values = popup.run()
        self.__add_item(table, values)

    def __map_add_port(self, coords):
        self.__map_add_item(Tables.PORTS, coords)

    def __map_add_warehouse(self, coords):
        self.__map_add_item(Tables.WAREHOUSES, coords)

    def __load_mapmarkers(self):
        self.map.delete_all_marker()

        data = self.db.get_table_data_all(Tables.PORTS)
        for row in data:
            if row["port_id"] is None:
                return

            id = row["port_id"]
            self.map.set_marker(
                row["latitude"], row["longitude"], text=row["name"],
                command=lambda x, id=id: self.__on_click_port_mark(x, id))

        data = self.db.get_table_data_all(Tables.WAREHOUSES)
        for row in data:
            if row["warehouse_id"] is None:
                return

            id = row["warehouse_id"]
            self.map.set_marker(
                row["latitude"], row["longitude"], text=row["name"],
                command=lambda x, id=id: self.__on_click_warehouse_mark(x, id),
                marker_color_circle="darkblue",
                marker_color_outside="blue"
            )

    def __display_table(self, table_name):
        self.remove_btr.configure(state="disabled")
        self.info_btr.configure(text="View Info", state="disabled")

        if not self.table_info is None:
            self.table_info.destroy()
            self.table_info = None
        self.table_view.delete_all()
        self.current_table = table_name

        self.table_opt.set(Tables.rget(table_name))
        self.table_opt.selection_clear()

        port_data = self.db.get_table_data_all(table_name)
        self.table_view.add_headings(list(port_data[0].keys()))

        for data in port_data:
            self.table_view.add_row(list(data.values()))
